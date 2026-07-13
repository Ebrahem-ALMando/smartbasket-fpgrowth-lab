"""Guarded support experiments and deterministic final-threshold selection."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from src.mining.fpgrowth_runner import run_fpgrowth
from src.mining.rule_generation import generate_rules


DEFAULT_SUPPORT_GRID = (0.05, 0.03, 0.02, 0.015, 0.01, 0.0075, 0.005)
CONFIDENCE_CANDIDATES = (0.30, 0.50, 0.70)


@dataclass(frozen=True)
class ResourceSafeguards:
    """Soft limits used to stop descending into impractical thresholds."""

    maximum_itemsets: int = 100_000
    maximum_rules: int = 250_000
    maximum_runtime_seconds: float = 300.0
    maximum_rss_delta_bytes: int = 2 * 1024**3


def support_count(minimum_support: float, transaction_count: int) -> int:
    """Translate proportional support to the conservative integer threshold."""
    if not 0 < minimum_support <= 1:
        raise ValueError("minimum_support must be within (0, 1]")
    if transaction_count < 1:
        raise ValueError("transaction_count must be positive")
    return math.ceil(minimum_support * transaction_count)


def run_threshold_sweep(
    basket: pd.DataFrame,
    *,
    transaction_count: int,
    descriptions: dict[str, str],
    support_grid: tuple[float, ...] = DEFAULT_SUPPORT_GRID,
    maximum_length: int | None = 3,
    safeguards: ResourceSafeguards = ResourceSafeguards(),
) -> pd.DataFrame:
    """Descend through support thresholds until a soft resource limit is hit."""
    records: list[dict[str, object]] = []
    stop_descending = False
    for threshold in support_grid:
        if stop_descending:
            records.append(
                {
                    "minimum_support": threshold,
                    "minimum_support_count": support_count(threshold, transaction_count),
                    "execution_status": "skipped_after_safeguard",
                    "stop_reason": "A previous threshold exceeded a soft resource safeguard.",
                }
            )
            continue
        try:
            run = run_fpgrowth(
                basket,
                minimum_support=threshold,
                maximum_length=maximum_length,
            )
            lengths = run.itemsets["itemsets"].map(len).value_counts()
            attempted = bool(lengths.drop(labels=1, errors="ignore").sum())
            rules = (
                generate_rules(
                    run.itemsets,
                    transaction_count=transaction_count,
                    descriptions=descriptions,
                    minimum_confidence=0.0,
                )
                if attempted
                else pd.DataFrame()
            )
            counts = {
                confidence: int((rules["confidence"] >= confidence).sum())
                if not rules.empty
                else 0
                for confidence in CONFIDENCE_CANDIDATES
            }
            record: dict[str, object] = {
                "minimum_support": threshold,
                "minimum_support_count": support_count(threshold, transaction_count),
                "frequent_itemset_count": len(run.itemsets),
                "length_1_count": int(lengths.get(1, 0)),
                "length_2_count": int(lengths.get(2, 0)),
                "length_3_count": int(lengths.get(3, 0)),
                "maximum_observed_length": int(lengths.index.max()),
                "runtime_seconds": run.benchmark.runtime_seconds,
                "rss_before_bytes": run.benchmark.rss_before_bytes,
                "rss_after_bytes": run.benchmark.rss_after_bytes,
                "approximate_rss_delta_bytes": run.benchmark.rss_delta_bytes,
                "memory_measurement": run.benchmark.memory_measurement,
                "rule_generation_attempted": attempted,
                "rule_generation_status": "success" if attempted else "not_applicable",
                "rule_count_confidence_0_30": counts[0.30],
                "rule_count_confidence_0_50": counts[0.50],
                "rule_count_confidence_0_70": counts[0.70],
                "execution_status": "success",
                "stop_reason": "",
                "maximum_length": maximum_length,
            }
            reasons = []
            if len(run.itemsets) > safeguards.maximum_itemsets:
                reasons.append("itemset_limit")
            if len(rules) > safeguards.maximum_rules:
                reasons.append("rule_limit")
            if run.benchmark.runtime_seconds > safeguards.maximum_runtime_seconds:
                reasons.append("runtime_limit")
            if abs(run.benchmark.rss_delta_bytes) > safeguards.maximum_rss_delta_bytes:
                reasons.append("rss_delta_limit")
            if reasons:
                record["execution_status"] = "success_resource_limit_reached"
                record["stop_reason"] = ",".join(reasons)
                stop_descending = True
            records.append(record)
        except Exception as exc:
            records.append(
                {
                    "minimum_support": threshold,
                    "minimum_support_count": support_count(threshold, transaction_count),
                    "execution_status": "failed",
                    "stop_reason": f"{type(exc).__name__}: {exc}",
                    "maximum_length": maximum_length,
                }
            )
            stop_descending = True
    return pd.DataFrame(records)


def select_final_support(
    sweep: pd.DataFrame,
    *,
    safeguards: ResourceSafeguards = ResourceSafeguards(),
) -> pd.Series:
    """Choose the lowest successful, non-trivial, reproducible threshold."""
    successful = sweep.loc[
        sweep["execution_status"].eq("success")
        & sweep["length_2_count"].gt(0)
        & sweep["length_3_count"].gt(0)
        & sweep["frequent_itemset_count"].le(safeguards.maximum_itemsets)
        & sweep["rule_count_confidence_0_50"].between(1, safeguards.maximum_rules)
        & sweep["runtime_seconds"].le(safeguards.maximum_runtime_seconds)
        & sweep["approximate_rss_delta_bytes"].abs().le(
            safeguards.maximum_rss_delta_bytes
        )
    ]
    if successful.empty:
        raise RuntimeError("No threshold satisfies the documented selection criteria")
    return successful.sort_values("minimum_support", ascending=True).iloc[0]


def select_final_confidence(final_sweep_row: pd.Series) -> float:
    """Choose the highest candidate retaining at least 25 manageable rules."""
    viable = []
    for confidence in sorted(CONFIDENCE_CANDIDATES, reverse=True):
        column = f"rule_count_confidence_{confidence:.2f}".replace(".", "_")
        count = int(final_sweep_row[column])
        if 25 <= count <= 50_000:
            viable.append(confidence)
    if viable:
        return viable[0]
    for confidence in sorted(CONFIDENCE_CANDIDATES, reverse=True):
        column = f"rule_count_confidence_{confidence:.2f}".replace(".", "_")
        if int(final_sweep_row[column]) > 0:
            return confidence
    raise RuntimeError("No candidate confidence produces any rule")
