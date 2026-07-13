"""Explicit Python-to-WEKA FPGrowth parameter alignment evidence."""

from __future__ import annotations

import pandas as pd


def build_parameter_alignment(effective: dict[str, object]) -> pd.DataFrame:
    """Build and validate the fixed alignment table from bridge introspection."""
    rows = [
        ("dataset scope", "United Kingdom", "-t", "full sparse ARFF", "aligned"),
        ("binary positive value", "True/present", "-P", effective.get("positive_index"), "aligned"),
        ("maximum itemset/rule size", 3, "-I", effective.get("maximum_items"), "aligned"),
        ("rule metric", "Confidence", "-T", effective.get("metric_type"), "aligned"),
        ("minimum confidence", 0.70, "-C", effective.get("minimum_metric"), "aligned"),
        ("minimum support", 0.005, "-M", effective.get("lower_minimum_support"), "aligned"),
        ("upper support", "no upper ceiling", "-U", effective.get("upper_minimum_support"), "aligned"),
        ("find all qualifying rules", True, "-S", effective.get("find_all_rules"), "aligned"),
        ("requested top-N", "not used", "-N", effective.get("requested_number_of_rules"), "ignored_in_find_all_mode"),
        ("support delta", "not used", "-D", effective.get("support_delta"), "ignored_when_find_all_enabled"),
        ("Phase 5 lift threshold", "not applied", "none", "not applied", "aligned"),
        ("class attribute", "none", "none", "none", "aligned"),
    ]
    table = pd.DataFrame(
        rows, columns=["concept", "python_value", "weka_option", "weka_value", "alignment_status"]
    )
    validate_parameter_alignment(table)
    return table


def validate_parameter_alignment(table: pd.DataFrame) -> None:
    """Reject silent semantic drift in material WEKA parameters."""
    lookup = table.set_index("concept")["weka_value"].to_dict()
    expected = {
        "binary positive value": 2,
        "maximum itemset/rule size": 3,
        "rule metric": "Confidence",
        "minimum confidence": 0.7,
        "minimum support": 0.005,
        "upper support": 1.0,
        "find all qualifying rules": True,
    }
    mismatches = {key: (expected_value, lookup.get(key)) for key, expected_value in expected.items() if lookup.get(key) != expected_value}
    if mismatches:
        raise ValueError(f"WEKA parameter alignment failed: {mismatches}")
