"""Strict parser for the machine-readable Java bridge rule export."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


RAW_RULE_COLUMNS = {
    "rule_index",
    "premise_aliases",
    "consequence_aliases",
    "premise_support_count",
    "consequence_support_count",
    "total_support_count",
    "transaction_count",
    "confidence",
    "lift",
    "leverage",
    "conviction",
    "primary_metric_name",
    "primary_metric_value",
    "metric_names",
    "metric_values",
    "weka_rule_text",
}


def _parse_aliases(value: object) -> tuple[str, ...]:
    parsed = json.loads(str(value))
    if not isinstance(parsed, list) or not parsed or not all(
        isinstance(item, str) and item for item in parsed
    ):
        raise ValueError("Rule sides must be non-empty JSON string arrays")
    aliases = tuple(parsed)
    if len(set(aliases)) != len(aliases):
        raise ValueError("A rule side contains duplicate aliases")
    return aliases


def parse_weka_rule_export(path: Path) -> pd.DataFrame:
    """Load bridge CSV and fail on missing schema or malformed logical rules."""
    rules = pd.read_csv(path)
    missing = RAW_RULE_COLUMNS.difference(rules.columns)
    if missing:
        raise ValueError(f"WEKA bridge output is missing columns: {sorted(missing)}")
    parsed = rules.copy()
    parsed["premise_alias_tuple"] = parsed["premise_aliases"].map(_parse_aliases)
    parsed["consequence_alias_tuple"] = parsed["consequence_aliases"].map(_parse_aliases)
    if parsed["rule_index"].duplicated().any():
        raise ValueError("WEKA bridge output contains duplicate rule_index values")
    numeric_counts = [
        "premise_support_count",
        "consequence_support_count",
        "total_support_count",
        "transaction_count",
    ]
    for column in numeric_counts:
        parsed[column] = pd.to_numeric(parsed[column], errors="raise").astype("int64")
    if (parsed[numeric_counts] < 0).any(axis=None):
        raise ValueError("WEKA bridge output contains negative counts")
    if (
        parsed["total_support_count"]
        > parsed[["premise_support_count", "consequence_support_count"]].min(axis=1)
    ).any():
        raise ValueError("Rule support exceeds a side support")
    for column in ("confidence", "lift", "leverage", "conviction"):
        parsed[column] = pd.to_numeric(parsed[column], errors="coerce")
    return parsed

