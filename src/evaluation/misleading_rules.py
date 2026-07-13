"""Transparent, non-binary warning flags for potentially misleading rules."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd


FLAG_COLUMNS = (
    "high_confidence_weak_lift",
    "common_consequent",
    "near_support_floor",
    "high_lift_low_count",
    "weak_bootstrap_stability",
    "wide_confidence_interval",
    "wide_lift_interval",
    "reciprocal_rule_exists",
    "equivalent_normalized_code",
    "insufficient_business_evidence",
)


def detect_misleading_flags(rules: pd.DataFrame) -> pd.DataFrame:
    """Calculate every frozen Phase 5 warning flag without hiding metrics."""
    result = pd.DataFrame({"rule_key": rules["rule_key"]})
    result["high_confidence_weak_lift"] = (
        rules["confidence"].ge(0.70) & rules["lift"].lt(1.50)
    )
    result["common_consequent"] = rules["consequent_support"].ge(0.08)
    result["near_support_floor"] = rules["support_count"].le(112)
    result["high_lift_low_count"] = rules["lift"].ge(10) & rules["support_count"].le(135)
    result["weak_bootstrap_stability"] = rules["rule_presence_rate"].lt(0.50)
    result["wide_confidence_interval"] = (
        rules["confidence_p975"] - rules["confidence_p025"]
    ).ge(0.20)
    lift_width = rules["lift_p975"] - rules["lift_p025"]
    result["wide_lift_interval"] = lift_width.gt(rules["lift_mean"]) | ~np.isfinite(lift_width)

    direct_keys = set()
    reverse_by_key: dict[str, str] = {}
    for row in rules.itertuples(index=False):
        antecedent = tuple(json.loads(row.antecedent_codes))
        consequent = tuple(json.loads(row.consequent_codes))
        if len(antecedent) == len(consequent) == 1:
            direct_keys.add(row.rule_key)
            reverse_by_key[row.rule_key] = f"{consequent[0]} => {antecedent[0]}"
    result["reciprocal_rule_exists"] = rules["rule_key"].map(
        lambda key: reverse_by_key.get(key, "") in direct_keys
    )
    result["equivalent_normalized_code"] = False
    core_flags = [
        "weak_bootstrap_stability",
        "wide_confidence_interval",
        "wide_lift_interval",
        "near_support_floor",
        "high_confidence_weak_lift",
    ]
    result["insufficient_business_evidence"] = (
        rules["stability_category"].eq("Unstable")
        | result[core_flags].sum(axis=1).ge(3)
        | rules[["support", "confidence", "lift"]].isna().any(axis=1)
    )
    result["flag_count"] = result[list(FLAG_COLUMNS)].sum(axis=1)
    result["quality_flags"] = result.apply(
        lambda row: " | ".join(flag for flag in FLAG_COLUMNS if bool(row[flag])) or "none",
        axis=1,
    )
    return result


def misleading_flag_summary(flags: pd.DataFrame) -> pd.DataFrame:
    """Return one count and percentage for each transparent flag."""
    return pd.DataFrame(
        {
            "flag": FLAG_COLUMNS,
            "rule_count": [int(flags[flag].sum()) for flag in FLAG_COLUMNS],
            "rule_percentage": [100 * float(flags[flag].mean()) for flag in FLAG_COLUMNS],
        }
    ).sort_values(["rule_count", "flag"], ascending=[False, True])
