"""Execute the reproducible Phase 3 Online Retail preparation pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.visualization.data_quality import create_phase3_figures

from .basket_matrix import build_binary_basket_matrix, save_basket_artifacts
from .cleaning import ADMINISTRATIVE_STOCK_CODES, REJECTION_ORDER, clean_purchase_records
from .data_audit import (
    administrative_candidates,
    quality_metrics,
    raw_missing_values,
    raw_quality_summary,
    raw_schema_summary,
)
from .export import save_csv
from .paths import ensure_directory, project_path
from .raw_loader import load_raw_workbook, verify_workbook_integrity, workbook_sheet_names
from .transactions import (
    country_summary,
    reconstruct_transactions,
    scope_comparison,
    select_core_scope,
    top_products_by_transaction_count,
    transaction_size_summary,
)


@dataclass(frozen=True)
class PipelineSummary:
    """Small set of executed Phase 3 facts used by validation and documentation."""

    raw_rows: int
    valid_line_items: int
    rejected_records: int
    transactions: int
    unique_products: int
    core_scope: str
    core_transactions: int
    basket_rows: int
    basket_columns: int
    basket_nonzero: int
    workbook_sha256: str


def _rejection_reason_table(rejected: pd.DataFrame, raw_count: int) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for reason, explanation, _ in REJECTION_ORDER:
        flag_count = int(rejected[reason].sum())
        primary_count = int(rejected["primary_rejection_reason"].eq(reason).sum())
        records.append(
            {
                "reason": reason,
                "explanation": explanation,
                "all_flagged_record_count": flag_count,
                "primary_sequential_record_count": primary_count,
                "percentage_of_raw_records_primary": primary_count / raw_count * 100,
                "percentage_of_rejected_records_primary": primary_count / len(rejected) * 100,
            }
        )
    return pd.DataFrame.from_records(records)


def _classified_administrative_lines(rejected: pd.DataFrame) -> pd.DataFrame:
    selected = rejected.loc[
        rejected["non_product_line"],
        ["StockCodeNormalized", "DescriptionNormalized", "primary_rejection_reason"],
    ].copy()
    selected["line_count"] = 1
    return (
        selected.groupby(
            ["StockCodeNormalized", "DescriptionNormalized", "primary_rejection_reason"],
            dropna=False,
            as_index=False,
        )["line_count"]
        .sum()
        .sort_values(["line_count", "StockCodeNormalized"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )


def run_pipeline() -> PipelineSummary:
    """Run raw validation, cleaning, reconstruction, sparse export, and figures."""
    for directory in (
        ("data", "interim"),
        ("data", "processed"),
        ("outputs", "tables"),
        ("outputs", "figures"),
    ):
        ensure_directory(*directory)

    checksum_before = verify_workbook_integrity()
    sheets = workbook_sheet_names()
    raw = load_raw_workbook()

    schema_table = raw_schema_summary(raw)
    missing_table = raw_missing_values(raw)
    raw_quality_table = raw_quality_summary(raw)
    save_csv(schema_table, project_path("outputs", "tables", "raw_schema.csv"))
    save_csv(missing_table, project_path("outputs", "tables", "raw_missing_values.csv"))
    save_csv(raw_quality_table, project_path("outputs", "tables", "raw_quality_summary.csv"))
    save_csv(
        administrative_candidates(raw),
        project_path("outputs", "tables", "administrative_candidates.csv"),
    )

    cleaning = clean_purchase_records(raw)
    save_csv(
        cleaning.accepted,
        project_path("data", "interim", "online_retail_valid_line_items.csv"),
    )
    save_csv(
        cleaning.rejected,
        project_path("data", "interim", "online_retail_rejected_records.csv"),
    )
    save_csv(
        cleaning.lineage,
        project_path("outputs", "tables", "data_cleaning_lineage.csv"),
    )
    rejection_table = _rejection_reason_table(cleaning.rejected, len(raw))
    save_csv(
        rejection_table,
        project_path("outputs", "tables", "cleaning_rejection_reasons.csv"),
    )
    save_csv(
        _classified_administrative_lines(cleaning.rejected),
        project_path("outputs", "tables", "administrative_lines_classified.csv"),
    )

    reconstructed = reconstruct_transactions(cleaning.accepted)
    save_csv(
        reconstructed.transactions,
        project_path("data", "processed", "online_retail_transactions.csv"),
    )
    save_csv(
        reconstructed.transaction_items,
        project_path("data", "processed", "online_retail_transaction_items.csv"),
    )

    scopes = scope_comparison(reconstructed.transactions, reconstructed.transaction_items)
    core_scope = select_core_scope(scopes)
    save_csv(scopes, project_path("outputs", "tables", "scope_comparison.csv"))
    if core_scope == "United Kingdom":
        core_transactions = reconstructed.transactions.loc[
            reconstructed.transactions["Country"].eq("United Kingdom")
        ].copy()
    else:
        core_transactions = reconstructed.transactions.copy()
    core_invoice_ids = set(core_transactions["InvoiceNo"])
    core_items = reconstructed.transaction_items.loc[
        reconstructed.transaction_items["InvoiceNo"].isin(core_invoice_ids)
    ].copy()

    basket = build_binary_basket_matrix(
        core_transactions,
        core_items,
        reconstructed.product_catalog,
    )
    save_basket_artifacts(
        basket,
        project_path("data", "processed", "online_retail_basket_matrix.npz"),
        project_path("data", "processed", "online_retail_basket_columns.json"),
        project_path("data", "processed", "online_retail_transaction_index.csv"),
    )

    transaction_sizes = transaction_size_summary(core_transactions)
    countries = country_summary(reconstructed.transactions, reconstructed.transaction_items)
    top_products = top_products_by_transaction_count(core_items, limit=50)
    save_csv(
        transaction_sizes,
        project_path("outputs", "tables", "transaction_size_summary.csv"),
    )
    save_csv(countries, project_path("outputs", "tables", "country_summary.csv"))
    save_csv(
        top_products,
        project_path("outputs", "tables", "top_products_by_transaction_count.csv"),
    )

    raw_metrics = quality_metrics(raw)
    processed_metrics = [
        ("workbook_sheet_names", "|".join(sheets)),
        ("raw_line_items", len(raw)),
        ("valid_line_items", len(cleaning.accepted)),
        ("rejected_or_separated_line_items", len(cleaning.rejected)),
        ("valid_transactions_all_countries", len(reconstructed.transactions)),
        ("unique_products_all_countries", reconstructed.transaction_items["StockCode"].nunique()),
        ("core_scope", core_scope),
        ("core_transactions", len(core_transactions)),
        ("core_unique_products", core_items["StockCode"].nunique()),
        ("basket_matrix_rows", basket.matrix.shape[0]),
        ("basket_matrix_columns", basket.matrix.shape[1]),
        ("basket_matrix_nonzero_entries", basket.matrix.nnz),
        ("basket_matrix_density", basket.matrix.nnz / (basket.matrix.shape[0] * basket.matrix.shape[1])),
        ("customer_conflict_transactions", reconstructed.transactions["HasCustomerConflict"].sum()),
        ("country_conflict_transactions", reconstructed.transactions["HasCountryConflict"].sum()),
        ("raw_duplicate_rows_beyond_first", raw_metrics["duplicate_rows_beyond_first"]),
        ("administrative_stock_codes_policy_count", len(ADMINISTRATIVE_STOCK_CODES)),
        ("raw_workbook_sha256", checksum_before),
    ]
    processed_summary = pd.DataFrame(processed_metrics, columns=["metric", "value"])
    save_csv(
        processed_summary,
        project_path("outputs", "tables", "processed_dataset_summary.csv"),
    )

    create_phase3_figures(
        top_products=top_products,
        core_transactions=core_transactions,
        all_transactions=reconstructed.transactions,
        country_table=countries,
        lineage=cleaning.lineage,
        missing_table=missing_table,
        output_directory=project_path("outputs", "figures"),
    )

    checksum_after = verify_workbook_integrity()
    if checksum_after != checksum_before:
        raise AssertionError("Raw workbook changed during pipeline execution")

    return PipelineSummary(
        raw_rows=len(raw),
        valid_line_items=len(cleaning.accepted),
        rejected_records=len(cleaning.rejected),
        transactions=len(reconstructed.transactions),
        unique_products=reconstructed.transaction_items["StockCode"].nunique(),
        core_scope=core_scope,
        core_transactions=len(core_transactions),
        basket_rows=basket.matrix.shape[0],
        basket_columns=basket.matrix.shape[1],
        basket_nonzero=basket.matrix.nnz,
        workbook_sha256=checksum_after,
    )


if __name__ == "__main__":
    print(run_pipeline())
