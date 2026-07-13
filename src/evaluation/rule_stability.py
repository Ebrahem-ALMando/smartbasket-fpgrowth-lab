"""Aggregate candidate-rule presence and empirical metric uncertainty."""

from __future__ import annotations

import pandas as pd

from src.evaluation.metric_uncertainty import metric_interval


STABILITY_ORDER = (
    "Very stable",
    "Moderately stable",
    "Weakly stable",
    "Unstable",
)


def stability_category(presence_rate: float) -> str:
    """Assign the frozen project-convention stability category."""
    if not 0 <= presence_rate <= 1:
        raise ValueError("presence_rate must be between zero and one")
    if presence_rate >= 0.80:
        return "Very stable"
    if presence_rate >= 0.50:
        return "Moderately stable"
    if presence_rate >= 0.20:
        return "Weakly stable"
    return "Unstable"


def aggregate_rule_stability(
    observations: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    successful_resamples: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate all Phase 4 candidates and return wide and long summaries."""
    if successful_resamples < 1:
        raise ValueError("At least one successful resample is required")
    rows: list[dict[str, object]] = []
    uncertainty_rows: list[dict[str, object]] = []
    grouped = observations.groupby("rule_key", sort=False)
    for rule_key in candidates["rule_key"]:
        group = grouped.get_group(rule_key) if rule_key in grouped.groups else pd.DataFrame()
        presence_count = int(group.get("is_present", pd.Series(dtype=bool)).sum())
        presence_rate = presence_count / successful_resamples
        row: dict[str, object] = {
            "rule_key": rule_key,
            "bootstrap_resamples_successful": successful_resamples,
            "rule_presence_count": presence_count,
            "rule_presence_rate": presence_rate,
            "stability_category": stability_category(presence_rate),
        }
        for metric in ("support", "confidence", "lift"):
            summary = metric_interval(
                group[metric] if metric in group else pd.Series(dtype=float)
            )
            for statistic, value in summary.items():
                row[f"{metric}_{statistic}"] = value
            uncertainty_rows.append(
                {"rule_key": rule_key, "metric": metric, **summary}
            )
        rows.append(row)
    stability = candidates.merge(pd.DataFrame(rows), on="rule_key", how="left")
    uncertainty = pd.DataFrame(uncertainty_rows)
    preferred = [
        ("rule_presence_rate", False),
        ("support_count", False),
        ("confidence", False),
        ("lift", False),
        ("rule_key", True),
    ]
    sort_columns = [column for column, _ in preferred if column in stability.columns]
    stability = stability.sort_values(
        sort_columns,
        ascending=[ascending for column, ascending in preferred if column in stability.columns],
        kind="mergesort",
    ).reset_index(drop=True)
    return stability, uncertainty


def stability_category_summary(stability: pd.DataFrame) -> pd.DataFrame:
    """Count every frozen category, including categories with zero rules."""
    counts = stability["stability_category"].value_counts()
    total = len(stability)
    return pd.DataFrame(
        {
            "stability_category": STABILITY_ORDER,
            "rule_count": [int(counts.get(category, 0)) for category in STABILITY_ORDER],
            "rule_percentage": [
                100 * int(counts.get(category, 0)) / total if total else 0.0
                for category in STABILITY_ORDER
            ],
            "category_definition": [
                "presence rate >= 0.80",
                "0.50 <= presence rate < 0.80",
                "0.20 <= presence rate < 0.50",
                "presence rate < 0.20",
            ],
        }
    )
