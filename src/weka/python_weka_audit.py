"""Rule-identity and metric audit for aligned Python and WEKA outputs."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.weka.weka_metrics import METRIC_TOLERANCES, values_match


AUDIT_METRICS = ("support", "confidence", "lift", "leverage", "conviction")


def aligned_python_rules(
    rules: pd.DataFrame,
    *,
    minimum_support: float = 0.005,
    minimum_support_count: int = 90,
    minimum_confidence: float = 0.70,
    maximum_items: int = 3,
) -> pd.DataFrame:
    """Apply only conditions represented in the WEKA core audit."""
    required = {
        "rule_key", "support", "support_count", "confidence",
        "antecedent_length", "consequent_length",
    }
    missing = required.difference(rules.columns)
    if missing:
        raise ValueError(f"Python rules are missing columns: {sorted(missing)}")
    return rules.loc[
        (rules["support"] + 1e-15 >= minimum_support)
        & (rules["support_count"] >= minimum_support_count)
        & (rules["confidence"] + 1e-15 >= minimum_confidence)
        & (rules["antecedent_length"] + rules["consequent_length"] <= maximum_items)
    ].copy()


def _finite_or_special(value: object) -> float:
    if value is None or pd.isna(value):
        return float("nan")
    return float(value)


def audit_python_weka_rules(
    python_rules: pd.DataFrame, weka_rules: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Outer-join logical rules and classify exact/tolerance/mismatch evidence."""
    python_duplicates = int(python_rules["rule_key"].duplicated(keep=False).sum())
    valid_weka = weka_rules.loc[weka_rules["mapping_valid"]].copy()
    weka_duplicates = int(valid_weka["rule_key"].duplicated(keep=False).sum())
    mapping_failures = int((~weka_rules["mapping_valid"]).sum())
    py_unique = python_rules.drop_duplicates("rule_key").copy()
    wk_unique = valid_weka.drop_duplicates("rule_key").copy()
    py_unique["source_rank"] = np.arange(1, len(py_unique) + 1)
    wk_unique["source_rank"] = np.arange(1, len(wk_unique) + 1)
    py = py_unique.set_index("rule_key")
    wk = wk_unique.set_index("rule_key")
    keys = sorted(set(py.index).union(wk.index))
    rows: list[dict[str, object]] = []
    difference_rows: list[dict[str, object]] = []
    exact_rules = tolerance_rules = mismatch_rules = missing_metric_rules = 0
    for key in keys:
        in_python, in_weka = key in py.index, key in wk.index
        presence = "common" if in_python and in_weka else "python_only" if in_python else "weka_only"
        row: dict[str, object] = {"rule_key": key, "presence_status": presence}
        row["python_source_rank"] = int(py.at[key, "source_rank"]) if in_python else None
        row["weka_source_rank"] = int(wk.at[key, "source_rank"]) if in_weka else None
        row["absolute_rank_difference"] = (
            abs(int(py.at[key, "source_rank"]) - int(wk.at[key, "source_rank"]))
            if in_python and in_weka else None
        )
        metric_statuses: list[str] = []
        if presence == "common":
            for metric in AUDIT_METRICS:
                left = _finite_or_special(py.at[key, metric]) if metric in py.columns else float("nan")
                right = _finite_or_special(wk.at[key, metric]) if metric in wk.columns else float("nan")
                missing = np.isnan(left) != np.isnan(right)
                exact = (left == right) or (np.isnan(left) and np.isnan(right))
                matched = values_match(left, right, METRIC_TOLERANCES[metric])
                status = "missing" if missing else "exact" if exact else "tolerance" if matched else "mismatch"
                metric_statuses.append(status)
                absolute = abs(left - right) if np.isfinite(left) and np.isfinite(right) else (0.0 if left == right else np.nan)
                scale = max(abs(left), abs(right)) if np.isfinite(left) and np.isfinite(right) else np.nan
                relative = absolute / scale if scale and np.isfinite(scale) else (0.0 if absolute == 0 else np.nan)
                row[f"python_{metric}"] = left
                row[f"weka_{metric}"] = right
                row[f"{metric}_absolute_difference"] = absolute
                row[f"{metric}_relative_difference"] = relative
                row[f"{metric}_match_status"] = status
                difference_rows.append(
                    {"rule_key": key, "metric": metric, "python_value": left,
                     "weka_value": right, "absolute_difference": absolute,
                     "relative_difference": relative, "match_status": status}
                )
            support_count_match = int(py.at[key, "support_count"]) == int(wk.at[key, "support_count"])
            row["support_count_exact_match"] = support_count_match
            if "missing" in metric_statuses:
                missing_metric_rules += 1
            if not support_count_match or "mismatch" in metric_statuses or "missing" in metric_statuses:
                row["overall_metric_status"] = "mismatch"
                mismatch_rules += 1
            elif all(status == "exact" for status in metric_statuses):
                row["overall_metric_status"] = "exact"
                exact_rules += 1
            else:
                row["overall_metric_status"] = "tolerance"
                tolerance_rules += 1
        else:
            row["overall_metric_status"] = "not_comparable"
        rows.append(row)
    audit = pd.DataFrame(rows)
    differences = pd.DataFrame(
        difference_rows,
        columns=[
            "rule_key", "metric", "python_value", "weka_value",
            "absolute_difference", "relative_difference", "match_status",
        ],
    )
    common = int((audit["presence_status"] == "common").sum())
    summary: dict[str, object] = {
        "python_rule_count": len(py),
        "weka_rule_count": len(wk),
        "common_rules": common,
        "python_only_rules": int((audit["presence_status"] == "python_only").sum()),
        "weka_only_rules": int((audit["presence_status"] == "weka_only").sum()),
        "exact_metric_matches": exact_rules,
        "tolerance_metric_matches": tolerance_rules,
        "metric_mismatches": mismatch_rules,
        "rules_with_missing_metrics": missing_metric_rules,
        "python_duplicate_rows": python_duplicates,
        "weka_duplicate_rows": weka_duplicates,
        "mapping_failures": mapping_failures,
        "tolerances": {
            name: {"absolute": value.absolute, "relative": value.relative}
            for name, value in METRIC_TOLERANCES.items()
        },
    }
    for metric in AUDIT_METRICS:
        subset = differences.loc[differences["metric"] == metric]
        status_counts = subset["match_status"].value_counts()
        summary[f"{metric}_exact_value_matches"] = int(status_counts.get("exact", 0))
        summary[f"{metric}_tolerance_value_matches"] = int(status_counts.get("tolerance", 0))
        summary[f"{metric}_value_mismatches"] = int(status_counts.get("mismatch", 0))
        summary[f"{metric}_missing_value_matches"] = int(status_counts.get("missing", 0))
        summary[f"maximum_{metric}_absolute_difference"] = (
            float(subset["absolute_difference"].max()) if not subset.empty else None
        )
        summary[f"maximum_{metric}_relative_difference"] = (
            float(subset["relative_difference"].max()) if not subset.empty else None
        )
    summary["exact_metric_value_matches"] = int(
        (differences["match_status"] == "exact").sum()
    )
    summary["tolerance_metric_value_matches"] = int(
        (differences["match_status"] == "tolerance").sum()
    )
    summary["metric_value_mismatches"] = int(
        (differences["match_status"] == "mismatch").sum()
    )
    if common + summary["python_only_rules"] != len(py):
        raise AssertionError("Python audit reconciliation failed")
    if common + summary["weka_only_rules"] != len(wk):
        raise AssertionError("WEKA audit reconciliation failed")
    return audit, differences, summary


def save_audit_outputs(
    audit: pd.DataFrame,
    differences: pd.DataFrame,
    summary: dict[str, object],
    *,
    output_directory: Path,
) -> None:
    """Persist the complete audit and disjoint unmatched-rule tables."""
    output_directory.mkdir(parents=True, exist_ok=True)
    audit.to_csv(output_directory / "python_weka_rule_audit.csv", index=False, encoding="utf-8", lineterminator="\n")
    differences.to_csv(output_directory / "python_weka_metric_differences.csv", index=False, encoding="utf-8", lineterminator="\n")
    audit.loc[audit["presence_status"] == "python_only"].to_csv(
        output_directory / "python_only_rules.csv", index=False, encoding="utf-8", lineterminator="\n"
    )
    audit.loc[audit["presence_status"] == "weka_only"].to_csv(
        output_directory / "weka_only_rules.csv", index=False, encoding="utf-8", lineterminator="\n"
    )
    (output_directory / "python_weka_rule_audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
