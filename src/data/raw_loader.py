"""Load and validate the official Online Retail workbook."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

import pandas as pd

from .paths import project_path


EXPECTED_COLUMNS: Final[tuple[str, ...]] = (
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
)

DEFAULT_WORKBOOK = project_path("data", "raw", "online_retail", "Online Retail.xlsx")
EXPECTED_WORKBOOK_SHA256: Final[str] = (
    "43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d"
)


def _identifier(value: object) -> object:
    """Preserve identifier semantics without adding decimal suffixes."""
    if pd.isna(value):
        return pd.NA
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def workbook_sheet_names(path: Path | None = None) -> list[str]:
    """Return workbook sheet names without modifying the file."""
    workbook = path or DEFAULT_WORKBOOK
    with pd.ExcelFile(workbook, engine="openpyxl") as excel_file:
        return list(excel_file.sheet_names)


def sha256_file(path: Path) -> str:
    """Calculate a file SHA-256 without loading the full file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_workbook_integrity(path: Path | None = None) -> str:
    """Verify the raw workbook against the recorded official-file checksum."""
    workbook = path or DEFAULT_WORKBOOK
    observed = sha256_file(workbook)
    if observed != EXPECTED_WORKBOOK_SHA256:
        raise ValueError(
            f"Raw workbook checksum mismatch: expected {EXPECTED_WORKBOOK_SHA256}, "
            f"observed {observed}"
        )
    return observed


def validate_expected_columns(frame: pd.DataFrame) -> None:
    """Raise a descriptive error when required raw columns are absent."""
    missing = [column for column in EXPECTED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required Online Retail columns: {missing}")


def load_raw_workbook(path: Path | None = None) -> pd.DataFrame:
    """Load the official workbook while preserving business identifiers."""
    workbook = path or DEFAULT_WORKBOOK
    if not workbook.is_file():
        raise FileNotFoundError(f"Online Retail workbook not found: {workbook}")

    frame = pd.read_excel(
        workbook,
        engine="openpyxl",
        converters={
            "InvoiceNo": _identifier,
            "StockCode": _identifier,
            "CustomerID": _identifier,
        },
    )
    validate_expected_columns(frame)
    frame = frame.loc[:, list(EXPECTED_COLUMNS)].copy()
    frame["Description"] = frame["Description"].astype("string")
    frame["Country"] = frame["Country"].astype("string")
    frame["InvoiceNo"] = frame["InvoiceNo"].astype("string")
    frame["StockCode"] = frame["StockCode"].astype("string")
    frame["CustomerID"] = frame["CustomerID"].astype("string")
    frame["Quantity"] = pd.to_numeric(frame["Quantity"], errors="coerce")
    frame["UnitPrice"] = pd.to_numeric(frame["UnitPrice"], errors="coerce")
    frame["InvoiceDate"] = pd.to_datetime(frame["InvoiceDate"], errors="coerce")
    return frame
