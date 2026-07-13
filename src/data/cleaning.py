"""Evidence-based cleaning for positive Online Retail purchase baskets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd

from .data_audit import cancellation_mask, invalid_price_mask, invalid_quantity_mask


ADMINISTRATIVE_STOCK_CODES: Final[frozenset[str]] = frozenset(
    {
        "POST",
        "DOT",
        "C2",
        "23444",
        "23574",
        "M",
        "D",
        "S",
        "BANK CHARGES",
        "AMAZONFEE",
        "CRUK",
        "B",
        "GIFT_0001_10",
        "GIFT_0001_20",
        "GIFT_0001_30",
        "GIFT_0001_40",
        "GIFT_0001_50",
    }
)

REJECTION_ORDER: Final[tuple[tuple[str, str, str], ...]] = (
    ("missing_invoice", "Missing invoice identifier", "Missing invoice identifiers"),
    ("cancelled_invoice", "Cancelled invoice", "Cancelled invoices"),
    ("invalid_quantity", "Missing or non-positive quantity", "Invalid quantities"),
    ("invalid_price", "Missing or non-positive unit price", "Invalid prices"),
    ("missing_description", "Missing product description", "Missing product descriptions"),
    ("non_product_line", "Observed administrative or non-product code", "Administrative lines"),
    ("duplicate_full_row", "Exact duplicate beyond first occurrence", "Duplicate records"),
)


@dataclass(frozen=True)
class CleaningResult:
    """Accepted records, rejected evidence, and sequential lineage."""

    accepted: pd.DataFrame
    rejected: pd.DataFrame
    lineage: pd.DataFrame


def normalize_product_description(series: pd.Series) -> pd.Series:
    """Normalize product text conservatively without fuzzy matching."""
    return (
        series.astype("string")
        .str.normalize("NFKC")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.upper()
    )


def _append_reason(reason_text: pd.Series, mask: pd.Series, reason: str) -> pd.Series:
    prefix = reason_text.where(reason_text.eq(""), reason_text + "|")
    return reason_text.mask(mask, prefix + reason)


def clean_purchase_records(frame: pd.DataFrame) -> CleaningResult:
    """Separate valid positive purchases from fully audited rejected records."""
    cleaned = frame.copy()
    cleaned["StockCodeNormalized"] = (
        cleaned["StockCode"].astype("string").str.strip().str.upper()
    )
    cleaned["DescriptionNormalized"] = normalize_product_description(cleaned["Description"])
    cleaned["CountryNormalized"] = (
        cleaned["Country"].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    )

    flags = pd.DataFrame(index=cleaned.index)
    flags["missing_invoice"] = cleaned["InvoiceNo"].isna() | cleaned["InvoiceNo"].str.strip().eq("")
    flags["cancelled_invoice"] = cancellation_mask(cleaned)
    flags["invalid_quantity"] = invalid_quantity_mask(cleaned)
    flags["invalid_price"] = invalid_price_mask(cleaned)
    flags["missing_description"] = cleaned["DescriptionNormalized"].isna() | cleaned[
        "DescriptionNormalized"
    ].eq("")
    flags["non_product_line"] = cleaned["StockCodeNormalized"].isin(ADMINISTRATIVE_STOCK_CODES)
    flags["duplicate_full_row"] = frame.duplicated(keep="first")

    reasons = pd.Series("", index=cleaned.index, dtype="string")
    for reason, _, _ in REJECTION_ORDER:
        reasons = _append_reason(reasons, flags[reason], reason)

    rejected_mask = flags.any(axis=1)
    primary_reason = pd.Series(pd.NA, index=cleaned.index, dtype="string")
    working = pd.Series(True, index=cleaned.index)
    lineage_records: list[dict[str, object]] = []
    for reason, explanation, policy_reference in REJECTION_ORDER:
        input_count = int(working.sum())
        separated_mask = working & flags[reason]
        separated_count = int(separated_mask.sum())
        primary_reason.loc[separated_mask] = reason
        working &= ~flags[reason]
        output_count = int(working.sum())
        lineage_records.append(
            {
                "step_name": reason,
                "input_record_count": input_count,
                "removed_or_separated_count": separated_count,
                "output_record_count": output_count,
                "percentage_affected": separated_count / input_count * 100 if input_count else 0.0,
                "reason": explanation,
                "policy_reference": f"DATA_CLEANING_POLICY.md — {policy_reference}",
            }
        )

    if not working.equals(~rejected_mask):
        raise AssertionError("Sequential lineage mask does not match rejection flags")

    accepted = cleaned.loc[~rejected_mask].copy()
    rejected = cleaned.loc[rejected_mask].copy()
    for column in flags.columns:
        rejected[column] = flags.loc[rejected_mask, column].astype(bool)
    rejected["rejection_reasons"] = reasons.loc[rejected_mask]
    rejected["primary_rejection_reason"] = primary_reason.loc[rejected_mask]

    lineage = pd.DataFrame.from_records(lineage_records)
    if int(lineage.iloc[-1]["output_record_count"]) != len(accepted):
        raise AssertionError("Final lineage count does not equal accepted record count")
    if len(accepted) + len(rejected) != len(frame):
        raise AssertionError("Accepted and rejected records do not reconcile to raw input")

    return CleaningResult(
        accepted=accepted.reset_index(drop=True),
        rejected=rejected.reset_index(drop=True),
        lineage=lineage,
    )
