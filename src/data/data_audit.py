"""Data-quality audits for the Online Retail raw workbook."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def cancellation_mask(frame: pd.DataFrame) -> pd.Series:
    """Identify cancelled invoice lines using UCI's documented convention."""
    return frame["InvoiceNo"].astype("string").str.upper().str.startswith("C", na=False)


def invalid_quantity_mask(frame: pd.DataFrame) -> pd.Series:
    """Identify missing, zero, or negative quantities."""
    return frame["Quantity"].isna() | frame["Quantity"].le(0)


def invalid_price_mask(frame: pd.DataFrame) -> pd.Series:
    """Identify missing, zero, or negative unit prices."""
    return frame["UnitPrice"].isna() | frame["UnitPrice"].le(0)


def raw_schema_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Return semantic schema, completeness, cardinality, and memory details."""
    rows = len(frame)
    records: list[dict[str, object]] = []
    for column in frame.columns:
        missing = int(frame[column].isna().sum())
        records.append(
            {
                "column_name": column,
                "dtype": str(frame[column].dtype),
                "non_null_count": rows - missing,
                "missing_count": missing,
                "missing_percentage": missing / rows * 100 if rows else 0.0,
                "unique_non_null": int(frame[column].nunique(dropna=True)),
                "memory_bytes": int(frame[column].memory_usage(index=False, deep=True)),
            }
        )
    return pd.DataFrame.from_records(records)


def raw_missing_values(frame: pd.DataFrame) -> pd.DataFrame:
    """Return missing-value counts and percentages by raw column."""
    rows = len(frame)
    missing = frame.isna().sum()
    return pd.DataFrame(
        {
            "column_name": missing.index,
            "missing_count": missing.astype("int64").values,
            "missing_percentage": (missing / rows * 100).values if rows else 0.0,
        }
    )


def quality_metrics(frame: pd.DataFrame) -> Mapping[str, object]:
    """Calculate auditable raw-data quality metrics."""
    cancelled = cancellation_mask(frame)
    invalid_quantity = invalid_quantity_mask(frame)
    invalid_price = invalid_price_mask(frame)
    negative_quantity = frame["Quantity"].lt(0)
    zero_quantity = frame["Quantity"].eq(0)
    negative_price = frame["UnitPrice"].lt(0)
    zero_price = frame["UnitPrice"].eq(0)
    return {
        "raw_rows": int(len(frame)),
        "raw_columns": int(frame.shape[1]),
        "raw_memory_bytes": int(frame.memory_usage(index=True, deep=True).sum()),
        "duplicate_full_rows": int(frame.duplicated(keep=False).sum()),
        "duplicate_rows_beyond_first": int(frame.duplicated(keep="first").sum()),
        "unique_invoices": int(frame["InvoiceNo"].nunique(dropna=True)),
        "unique_stock_codes": int(frame["StockCode"].nunique(dropna=True)),
        "unique_descriptions": int(frame["Description"].nunique(dropna=True)),
        "unique_customers": int(frame["CustomerID"].nunique(dropna=True)),
        "unique_countries": int(frame["Country"].nunique(dropna=True)),
        "first_invoice_date": frame["InvoiceDate"].min(),
        "last_invoice_date": frame["InvoiceDate"].max(),
        "cancelled_line_items": int(cancelled.sum()),
        "cancelled_invoices": int(frame.loc[cancelled, "InvoiceNo"].nunique(dropna=True)),
        "negative_quantity_records": int(negative_quantity.sum()),
        "zero_quantity_records": int(zero_quantity.sum()),
        "invalid_quantity_records": int(invalid_quantity.sum()),
        "non_cancelled_negative_quantity_records": int((~cancelled & negative_quantity).sum()),
        "negative_price_records": int(negative_price.sum()),
        "zero_price_records": int(zero_price.sum()),
        "invalid_price_records": int(invalid_price.sum()),
        "missing_invoice_records": int(frame["InvoiceNo"].isna().sum()),
        "missing_description_records": int(frame["Description"].isna().sum()),
        "missing_customer_records": int(frame["CustomerID"].isna().sum()),
    }


def raw_quality_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Return raw quality metrics in a machine-readable long table."""
    metrics = quality_metrics(frame)
    notes = {
        "duplicate_full_rows": "All rows participating in a duplicate group.",
        "duplicate_rows_beyond_first": "Rows removable when retaining the first exact row.",
        "cancelled_line_items": "InvoiceNo begins with C, case-insensitive.",
        "invalid_quantity_records": "Quantity is missing or non-positive.",
        "invalid_price_records": "UnitPrice is missing or non-positive.",
    }
    return pd.DataFrame(
        {
            "metric": list(metrics.keys()),
            "value": [str(value) for value in metrics.values()],
            "notes": [notes.get(metric, "") for metric in metrics],
        }
    )


def administrative_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Surface observed non-product candidates for evidence-based policy review."""
    descriptions = frame["Description"].astype("string").str.upper()
    keyword_pattern = (
        r"POSTAGE|CARRIAGE|CHARGE|COMMISSION|DISCOUNT|MANUAL|AMAZON|"
        r"ADJUST|DOTCOM|BANK|TEST|SAMPLES?"
    )
    unusual_code = ~frame["StockCode"].astype("string").str.match(
        r"^\d{5}[A-Z]?$", na=False
    )
    candidate_mask = descriptions.str.contains(keyword_pattern, regex=True, na=False) | unusual_code
    candidates = frame.loc[candidate_mask, ["StockCode", "Description"]].copy()
    candidates["line_count"] = 1
    return (
        candidates.groupby(["StockCode", "Description"], dropna=False, as_index=False)["line_count"]
        .sum()
        .sort_values(["line_count", "StockCode"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )
