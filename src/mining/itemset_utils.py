"""Stable itemset keys, descriptions, and CSV-safe result serialization."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping

import pandas as pd


KEY_SEPARATOR = " | "


def canonical_itemset(items: Iterable[str]) -> tuple[str, ...]:
    """Return unique product codes in deterministic lexical order."""
    return tuple(sorted({str(item) for item in items}))


def itemset_key(items: Iterable[str]) -> str:
    """Return a stable human- and machine-comparable itemset key."""
    return KEY_SEPARATOR.join(canonical_itemset(items))


def serialize_items(items: Iterable[str]) -> str:
    """Serialize canonical items as a JSON array safe for CSV round trips."""
    return json.dumps(canonical_itemset(items), ensure_ascii=False)


def describe_items(items: Iterable[str], descriptions: Mapping[str, str]) -> tuple[str, ...]:
    """Map product codes to conservative display labels."""
    return tuple(
        f"{code} — {descriptions.get(code, 'Description unavailable')}"
        for code in canonical_itemset(items)
    )


def canonicalize_frequent_itemsets(
    frequent_itemsets: pd.DataFrame,
    *,
    transaction_count: int,
    descriptions: Mapping[str, str],
) -> pd.DataFrame:
    """Convert mlxtend itemsets into a stable, documented export schema."""
    required = {"support", "itemsets"}
    missing = required.difference(frequent_itemsets.columns)
    if missing:
        raise ValueError(f"Frequent-itemset table is missing columns: {sorted(missing)}")
    rows = []
    for row in frequent_itemsets.itertuples(index=False):
        codes = canonical_itemset(row.itemsets)
        support = float(row.support)
        rows.append(
            {
                "itemset_key": itemset_key(codes),
                "product_codes": serialize_items(codes),
                "product_descriptions": json.dumps(
                    describe_items(codes, descriptions), ensure_ascii=False
                ),
                "itemset_length": len(codes),
                "support": support,
                "support_count": int(round(support * transaction_count)),
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["support", "itemset_length", "itemset_key"],
            ascending=[False, True, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )


def restore_mlxtend_itemsets(canonical: pd.DataFrame) -> pd.DataFrame:
    """Restore the minimal support/itemsets schema from a canonical export."""
    return pd.DataFrame(
        {
            "support": canonical["support"].astype(float),
            "itemsets": canonical["product_codes"].map(
                lambda value: frozenset(json.loads(value))
            ),
        }
    )
