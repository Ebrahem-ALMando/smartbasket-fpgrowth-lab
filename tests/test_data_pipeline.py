"""Focused logic tests using small educational in-memory fixtures only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.basket_matrix import build_binary_basket_matrix
from src.data.cleaning import clean_purchase_records
from src.data.data_audit import cancellation_mask
from src.data.paths import PROJECT_ROOT, project_path
from src.data.raw_loader import EXPECTED_COLUMNS, validate_expected_columns
from src.data.transactions import reconstruct_transactions


def make_fixture(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Create a minimal schema-valid fixture; it is not a project result."""
    frame = pd.DataFrame(rows)
    for column in EXPECTED_COLUMNS:
        if column not in frame:
            frame[column] = pd.NA
    frame = frame.loc[:, list(EXPECTED_COLUMNS)]
    for column in ("InvoiceNo", "StockCode", "Description", "CustomerID", "Country"):
        frame[column] = frame[column].astype("string")
    frame["InvoiceDate"] = pd.to_datetime(frame["InvoiceDate"])
    frame["Quantity"] = pd.to_numeric(frame["Quantity"])
    frame["UnitPrice"] = pd.to_numeric(frame["UnitPrice"])
    return frame


def valid_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "InvoiceNo": "100",
        "StockCode": "A1",
        "Description": "Alpha product",
        "Quantity": 1,
        "InvoiceDate": "2011-01-01 10:00:00",
        "UnitPrice": 2.5,
        "CustomerID": "1",
        "Country": "United Kingdom",
    }
    row.update(overrides)
    return row


def test_expected_column_validation_rejects_missing_column() -> None:
    frame = pd.DataFrame(columns=[column for column in EXPECTED_COLUMNS if column != "InvoiceNo"])
    with pytest.raises(ValueError, match="InvoiceNo"):
        validate_expected_columns(frame)


def test_cancellation_detection_is_case_insensitive() -> None:
    frame = make_fixture(
        [
            valid_row(InvoiceNo="C100"),
            valid_row(InvoiceNo="c101"),
            valid_row(InvoiceNo="102"),
        ]
    )
    assert cancellation_mask(frame).tolist() == [True, True, False]


def test_invalid_quantity_is_separated() -> None:
    frame = make_fixture([valid_row(InvoiceNo="100"), valid_row(InvoiceNo="101", Quantity=0)])
    result = clean_purchase_records(frame)
    assert len(result.accepted) == 1
    assert result.rejected.iloc[0]["primary_rejection_reason"] == "invalid_quantity"


def test_missing_description_is_not_guessed() -> None:
    frame = make_fixture([valid_row(Description=pd.NA)])
    result = clean_purchase_records(frame)
    assert result.accepted.empty
    assert result.rejected.iloc[0]["missing_description"]
    assert pd.isna(result.rejected.iloc[0]["DescriptionNormalized"])


def test_exact_duplicate_keeps_first_and_audits_later_copy() -> None:
    row = valid_row()
    result = clean_purchase_records(make_fixture([row, row.copy()]))
    assert len(result.accepted) == 1
    assert len(result.rejected) == 1
    assert result.rejected.iloc[0]["primary_rejection_reason"] == "duplicate_full_row"


def test_transaction_aggregation_combines_repeated_invoice_product_lines() -> None:
    frame = make_fixture(
        [
            valid_row(Quantity=1),
            valid_row(Quantity=2, UnitPrice=3.0),
            valid_row(StockCode="B2", Description="Beta product", Quantity=1),
        ]
    )
    reconstructed = reconstruct_transactions(clean_purchase_records(frame).accepted)
    alpha = reconstructed.transaction_items.loc[
        reconstructed.transaction_items["StockCode"].eq("A1")
    ].iloc[0]
    assert alpha["Quantity"] == 3
    assert alpha["SourceLineCount"] == 2
    assert reconstructed.transactions.iloc[0]["UniqueProducts"] == 2


def test_binary_basket_encoding_and_stable_product_order() -> None:
    frame = make_fixture(
        [
            valid_row(InvoiceNo="101", StockCode="Z9", Description="Zulu"),
            valid_row(InvoiceNo="100", StockCode="A1", Description="Alpha"),
            valid_row(InvoiceNo="100", StockCode="Z9", Description="Zulu"),
        ]
    )
    reconstructed = reconstruct_transactions(clean_purchase_records(frame).accepted)
    artifacts = build_binary_basket_matrix(
        reconstructed.transactions,
        reconstructed.transaction_items,
        reconstructed.product_catalog,
    )
    assert artifacts.column_metadata["StockCode"].tolist() == ["A1", "Z9"]
    assert artifacts.matrix.shape == (2, 2)
    assert np.array_equal(np.unique(artifacts.matrix.data), np.array([1], dtype=np.uint8))


def test_project_paths_are_relative_to_root_and_cannot_escape() -> None:
    assert project_path("outputs", "tables").is_relative_to(PROJECT_ROOT)
    with pytest.raises(ValueError, match="escapes"):
        project_path("..", "outside")


def test_lineage_counts_reconcile() -> None:
    frame = make_fixture(
        [
            valid_row(InvoiceNo="100"),
            valid_row(InvoiceNo="C101", Quantity=-1),
            valid_row(InvoiceNo="102", UnitPrice=0),
            valid_row(InvoiceNo="103", Description=pd.NA),
        ]
    )
    result = clean_purchase_records(frame)
    lineage = result.lineage
    assert lineage.iloc[0]["input_record_count"] == len(frame)
    assert lineage.iloc[-1]["output_record_count"] == len(result.accepted)
    assert lineage["removed_or_separated_count"].sum() == len(result.rejected)
    assert len(result.accepted) + len(result.rejected) == len(frame)
