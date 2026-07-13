"""Reconstruct invoice transactions from cleaned Online Retail line items."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TransactionResult:
    """Reconstructed transaction tables and stable product catalog."""

    transactions: pd.DataFrame
    transaction_items: pd.DataFrame
    product_catalog: pd.DataFrame


def _product_catalog(valid: pd.DataFrame) -> pd.DataFrame:
    counts = (
        valid.groupby(["StockCodeNormalized", "DescriptionNormalized"], dropna=False)
        .size()
        .rename("description_line_count")
        .reset_index()
    )
    catalog = (
        counts.sort_values(
            ["StockCodeNormalized", "description_line_count", "DescriptionNormalized"],
            ascending=[True, False, True],
            kind="stable",
        )
        .drop_duplicates("StockCodeNormalized", keep="first")
        .rename(
            columns={
                "StockCodeNormalized": "StockCode",
                "DescriptionNormalized": "Description",
            }
        )
        .sort_values("StockCode", kind="stable")
        .reset_index(drop=True)
    )
    catalog["ProductLabel"] = catalog["StockCode"] + " — " + catalog["Description"]
    return catalog


def reconstruct_transactions(valid: pd.DataFrame) -> TransactionResult:
    """Aggregate repeated invoice-product lines and preserve invoice metadata."""
    if valid.empty:
        raise ValueError("Cannot reconstruct transactions from an empty valid-record table")

    catalog = _product_catalog(valid)
    items = (
        valid.groupby(["InvoiceNo", "StockCodeNormalized"], as_index=False, dropna=False)
        .agg(
            Quantity=("Quantity", "sum"),
            SourceLineCount=("Quantity", "size"),
            UnitPriceMin=("UnitPrice", "min"),
            UnitPriceMax=("UnitPrice", "max"),
            FirstLineDate=("InvoiceDate", "min"),
        )
        .rename(columns={"StockCodeNormalized": "StockCode"})
    )
    items = items.merge(catalog[["StockCode", "Description", "ProductLabel"]], on="StockCode", how="left")
    items = items.sort_values(["InvoiceNo", "StockCode"], kind="stable").reset_index(drop=True)

    metadata = (
        valid.groupby("InvoiceNo", as_index=False)
        .agg(
            InvoiceDate=("InvoiceDate", "min"),
            InvoiceDateMax=("InvoiceDate", "max"),
            CustomerID=("CustomerID", "first"),
            Country=("CountryNormalized", "first"),
            CustomerValueCount=("CustomerID", lambda values: values.nunique(dropna=True)),
            CountryValueCount=("CountryNormalized", lambda values: values.nunique(dropna=True)),
            SourceLineCount=("InvoiceNo", "size"),
        )
    )
    item_stats = (
        items.groupby("InvoiceNo", as_index=False)
        .agg(
            UniqueProducts=("StockCode", "size"),
            TotalQuantity=("Quantity", "sum"),
            AggregatedSourceLineCount=("SourceLineCount", "sum"),
        )
    )
    transactions = metadata.merge(item_stats, on="InvoiceNo", how="inner")
    transactions["HasCustomerConflict"] = transactions["CustomerValueCount"].gt(1)
    transactions["HasCountryConflict"] = transactions["CountryValueCount"].gt(1)
    transactions = transactions.sort_values(["InvoiceDate", "InvoiceNo"], kind="stable").reset_index(drop=True)

    if not transactions["SourceLineCount"].equals(transactions["AggregatedSourceLineCount"]):
        raise AssertionError("Aggregated transaction-item source counts do not reconcile")
    if items.duplicated(["InvoiceNo", "StockCode"]).any():
        raise AssertionError("Transaction items are not unique by invoice and product")
    if items["Quantity"].le(0).any():
        raise AssertionError("Non-positive aggregate quantity reached reconstructed transactions")

    return TransactionResult(
        transactions=transactions,
        transaction_items=items,
        product_catalog=catalog,
    )


def transaction_size_summary(transactions: pd.DataFrame) -> pd.DataFrame:
    """Return descriptive statistics for unique products per transaction."""
    summary = transactions["UniqueProducts"].describe(
        percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    )
    return summary.rename_axis("statistic").reset_index(name="value")


def country_summary(
    transactions: pd.DataFrame, transaction_items: pd.DataFrame
) -> pd.DataFrame:
    """Summarize transaction and product coverage by country."""
    item_countries = transaction_items[["InvoiceNo", "StockCode"]].merge(
        transactions[["InvoiceNo", "Country"]], on="InvoiceNo", how="left"
    )
    transaction_counts = transactions.groupby("Country", dropna=False).agg(
        transaction_count=("InvoiceNo", "size"),
        median_basket_size=("UniqueProducts", "median"),
        mean_basket_size=("UniqueProducts", "mean"),
        first_invoice_date=("InvoiceDate", "min"),
        last_invoice_date=("InvoiceDate", "max"),
    )
    products = item_countries.groupby("Country", dropna=False)["StockCode"].nunique().rename(
        "unique_products"
    )
    result = transaction_counts.join(products).reset_index()
    result["transaction_share_percentage"] = (
        result["transaction_count"] / len(transactions) * 100 if len(transactions) else 0.0
    )
    return result.sort_values("transaction_count", ascending=False, kind="stable").reset_index(drop=True)


def top_products_by_transaction_count(
    transaction_items: pd.DataFrame, limit: int = 50
) -> pd.DataFrame:
    """Rank products by the number of distinct valid transactions."""
    ranked = (
        transaction_items.groupby(["StockCode", "Description", "ProductLabel"], as_index=False)
        .agg(
            transaction_count=("InvoiceNo", "nunique"),
            total_quantity=("Quantity", "sum"),
        )
        .sort_values(["transaction_count", "StockCode"], ascending=[False, True], kind="stable")
    )
    return ranked.head(limit).reset_index(drop=True)


def scope_comparison(
    transactions: pd.DataFrame, transaction_items: pd.DataFrame
) -> pd.DataFrame:
    """Compare all valid transactions with the United Kingdom subset."""
    records: list[dict[str, object]] = []
    scopes = {
        "All countries": pd.Series(True, index=transactions.index),
        "United Kingdom": transactions["Country"].eq("United Kingdom"),
    }
    for name, transaction_mask in scopes.items():
        scoped_transactions = transactions.loc[transaction_mask]
        invoice_ids = set(scoped_transactions["InvoiceNo"])
        scoped_items = transaction_items[transaction_items["InvoiceNo"].isin(invoice_ids)]
        records.append(
            {
                "scope": name,
                "transaction_count": int(len(scoped_transactions)),
                "unique_products": int(scoped_items["StockCode"].nunique()),
                "median_basket_size": float(scoped_transactions["UniqueProducts"].median()),
                "mean_basket_size": float(scoped_transactions["UniqueProducts"].mean()),
                "first_invoice_date": scoped_transactions["InvoiceDate"].min(),
                "last_invoice_date": scoped_transactions["InvoiceDate"].max(),
                "transaction_share_percentage": (
                    len(scoped_transactions) / len(transactions) * 100 if len(transactions) else 0.0
                ),
                "expected_basket_matrix_width": int(scoped_items["StockCode"].nunique()),
                "interpretability_implication": (
                    "Multiple national markets and possible assortment differences."
                    if name == "All countries"
                    else "Single dominant market context with more consistent assortment."
                ),
            }
        )
    return pd.DataFrame.from_records(records)


def select_core_scope(scope_table: pd.DataFrame) -> str:
    """Select a reproducible core scope using documented Phase 3 priorities."""
    uk = scope_table.loc[scope_table["scope"].eq("United Kingdom")].iloc[0]
    if uk["transaction_count"] >= 10_000 and uk["transaction_share_percentage"] >= 75.0:
        return "United Kingdom"
    return "All countries"
