"""Guarded, reproducible transaction-level Bootstrap rule-stability pipeline."""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import psutil
from mlxtend.frequent_patterns import association_rules

from src.data.export import save_csv
from src.data.paths import project_path
from src.evaluation.rule_stability import (
    aggregate_rule_stability,
    stability_category_summary,
)
from src.mining.basket_loader import PreparedBasket, load_prepared_basket
from src.mining.fpgrowth_runner import run_fpgrowth
from src.mining.itemset_utils import itemset_key


INITIAL_BOOTSTRAP_SEEDS = tuple(range(51001, 51021))
EXPANSION_BOOTSTRAP_SEEDS = tuple(range(51021, 51031))


@dataclass(frozen=True)
class BootstrapConfig:
    """Frozen Phase 5 resampling and resource configuration."""

    minimum_support: float = 0.005
    minimum_confidence: float = 0.70
    minimum_lift: float = 1.20
    maximum_length: int = 3
    maximum_runtime_seconds: float = 120.0
    maximum_itemsets: int = 100_000
    maximum_rules: int = 250_000
    maximum_rss_delta_bytes: int = 2 * 1024**3
    expansion_total_runtime_seconds: float = 300.0
    expansion_median_runtime_seconds: float = 12.0


def bootstrap_indices(transaction_count: int, seed: int) -> np.ndarray:
    """Draw a deterministic same-size transaction sample with replacement."""
    if transaction_count < 1:
        raise ValueError("transaction_count must be positive")
    return np.random.default_rng(seed).integers(
        0, transaction_count, size=transaction_count, dtype=np.int64
    )


def _candidate_metrics(
    itemsets: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    transaction_count: int,
    config: BootstrapConfig,
) -> tuple[pd.DataFrame, int]:
    raw = association_rules(
        itemsets[["support", "itemsets"]],
        num_itemsets=transaction_count,
        metric="confidence",
        min_threshold=0.0,
        return_metrics=[
            "antecedent support",
            "consequent support",
            "support",
            "confidence",
            "lift",
        ],
    )
    raw["rule_key"] = raw.apply(
        lambda row: f"{itemset_key(row['antecedents'])} => {itemset_key(row['consequents'])}",
        axis=1,
    )
    raw_rule_count = len(raw)
    matched = raw.loc[
        raw["rule_key"].isin(set(candidates["rule_key"])),
        ["rule_key", "support", "confidence", "lift"],
    ].drop_duplicates("rule_key")
    result = candidates[["rule_key"]].merge(matched, on="rule_key", how="left")
    result["support_count"] = (
        result["support"] * transaction_count
    ).round().astype("Int64")
    minimum_count = math.ceil(config.minimum_support * transaction_count)
    result["is_present"] = (
        result["support"].ge(config.minimum_support)
        & result["support_count"].ge(minimum_count)
        & result["confidence"].ge(config.minimum_confidence)
        & result["lift"].ge(config.minimum_lift)
    )
    return result, raw_rule_count


def run_bootstrap_resample(
    prepared: PreparedBasket,
    candidates: pd.DataFrame,
    *,
    seed: int,
    resample_id: int,
    config: BootstrapConfig,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Run one independent resample and return candidate observations and metadata."""
    process = psutil.Process()
    before_rss = process.memory_info().rss
    started = perf_counter()
    indices = bootstrap_indices(prepared.transaction_count, seed)
    index_checksum = hashlib.sha256(indices.tobytes()).hexdigest()
    metadata: dict[str, object] = {
        "resample_id": resample_id,
        "seed": seed,
        "sample_size": len(indices),
        "unique_source_transactions": int(np.unique(indices).size),
        "sampling_method": "transaction rows sampled with replacement",
        "index_sha256": index_checksum,
        "minimum_support": config.minimum_support,
        "minimum_support_count": math.ceil(
            config.minimum_support * prepared.transaction_count
        ),
        "maximum_length": config.maximum_length,
        "status": "failed",
        "failure_reason": "",
    }
    try:
        sample_matrix = prepared.matrix[indices]
        sample_frame = pd.DataFrame.sparse.from_spmatrix(
            sample_matrix.astype(bool, copy=False),
            columns=list(prepared.product_codes),
        )
        run = run_fpgrowth(
            sample_frame,
            minimum_support=config.minimum_support,
            maximum_length=config.maximum_length,
        )
        metadata["frequent_itemset_count"] = len(run.itemsets)
        if len(run.itemsets) > config.maximum_itemsets:
            raise RuntimeError(
                f"itemset safeguard exceeded: {len(run.itemsets)} > {config.maximum_itemsets}"
            )
        observations, raw_rule_count = _candidate_metrics(
            run.itemsets,
            candidates,
            transaction_count=prepared.transaction_count,
            config=config,
        )
        metadata["raw_rule_count"] = raw_rule_count
        if raw_rule_count > config.maximum_rules:
            raise RuntimeError(
                f"rule safeguard exceeded: {raw_rule_count} > {config.maximum_rules}"
            )
        observations.insert(0, "seed", seed)
        observations.insert(0, "resample_id", resample_id)
        metadata["candidate_rules_matched"] = int(observations["support"].notna().sum())
        metadata["candidate_rules_present"] = int(observations["is_present"].sum())
        metadata["status"] = "success"
    except Exception as exc:
        observations = pd.DataFrame()
        metadata["failure_reason"] = f"{type(exc).__name__}: {exc}"
    runtime = perf_counter() - started
    after_rss = process.memory_info().rss
    metadata.update(
        {
            "runtime_seconds": runtime,
            "rss_before_bytes": before_rss,
            "rss_after_bytes": after_rss,
            "approximate_rss_delta_bytes": after_rss - before_rss,
            "memory_measurement": "approximate process RSS before/after; not peak memory",
        }
    )
    if metadata["status"] == "success" and runtime > config.maximum_runtime_seconds:
        metadata["status"] = "success_runtime_safeguard_reached"
        metadata["failure_reason"] = "runtime exceeded soft limit; expansion disabled"
    return observations, metadata


def _should_expand(metadata: pd.DataFrame, config: BootstrapConfig) -> bool:
    successful = metadata[metadata["status"].eq("success")]
    return bool(
        len(successful) == len(INITIAL_BOOTSTRAP_SEEDS)
        and successful["runtime_seconds"].sum()
        <= config.expansion_total_runtime_seconds
        and successful["runtime_seconds"].median()
        <= config.expansion_median_runtime_seconds
        and successful["approximate_rss_delta_bytes"].abs().max()
        <= config.maximum_rss_delta_bytes
    )


def run_bootstrap_experiment(
    *,
    config: BootstrapConfig = BootstrapConfig(),
    allow_expansion: bool = True,
) -> dict[str, object]:
    """Run 20 guarded resamples, optionally expanding only under frozen criteria."""
    prepared = load_prepared_basket()
    candidates = pd.read_csv(
        project_path("outputs", "tables", "association_rules_selected.csv")
    )
    all_observations: list[pd.DataFrame] = []
    metadata_records: list[dict[str, object]] = []
    interim_path = project_path(
        "data", "interim", "bootstrap_candidate_rule_metrics.csv"
    )

    def execute(seeds: tuple[int, ...], offset: int) -> None:
        for position, seed in enumerate(seeds, start=1):
            observations, metadata = run_bootstrap_resample(
                prepared,
                candidates,
                seed=seed,
                resample_id=offset + position,
                config=config,
            )
            metadata_records.append(metadata)
            if not observations.empty:
                all_observations.append(observations)
            if all_observations:
                save_csv(pd.concat(all_observations, ignore_index=True), interim_path)
            save_csv(
                pd.DataFrame(metadata_records),
                project_path("outputs", "tables", "bootstrap_run_metadata.csv"),
            )

    execute(INITIAL_BOOTSTRAP_SEEDS, 0)
    initial_metadata = pd.DataFrame(metadata_records)
    expanded = bool(allow_expansion and _should_expand(initial_metadata, config))
    if expanded:
        execute(EXPANSION_BOOTSTRAP_SEEDS, len(INITIAL_BOOTSTRAP_SEEDS))

    metadata_frame = pd.DataFrame(metadata_records)
    successful_mask = metadata_frame["status"].str.startswith("success")
    successful_count = int(successful_mask.sum())
    if successful_count == 0:
        raise RuntimeError("Every Bootstrap resample failed; stability cannot be computed")
    observations = pd.concat(all_observations, ignore_index=True)
    stability, uncertainty = aggregate_rule_stability(
        observations,
        candidates,
        successful_resamples=successful_count,
    )
    categories = stability_category_summary(stability)
    stable = stability[stability["rule_presence_rate"] >= 0.80].copy()
    unstable = stability[stability["rule_presence_rate"] < 0.20].copy()
    save_csv(stability, project_path("outputs", "tables", "rule_stability_results.csv"))
    save_csv(categories, project_path("outputs", "tables", "rule_stability_categories.csv"))
    save_csv(stable, project_path("outputs", "tables", "stable_rules.csv"))
    save_csv(unstable, project_path("outputs", "tables", "unstable_rules.csv"))
    save_csv(uncertainty, project_path("outputs", "tables", "rule_metric_uncertainty.csv"))
    failures = metadata_frame.loc[~successful_mask].copy()
    if failures.empty:
        failures = pd.DataFrame(columns=metadata_frame.columns)
    save_csv(
        failures,
        project_path("outputs", "comparisons", "bootstrap_failures.csv"),
    )
    summary = {
        "resamples_requested": len(metadata_records),
        "resamples_completed": successful_count,
        "initial_resamples": len(INITIAL_BOOTSTRAP_SEEDS),
        "expanded_to_30": expanded,
        "successful_runs": successful_count,
        "failed_or_stopped_runs": int((~successful_mask).sum()),
        "total_runtime_seconds": float(metadata_frame["runtime_seconds"].sum()),
        "median_runtime_seconds": float(metadata_frame.loc[successful_mask, "runtime_seconds"].median()),
        "maximum_runtime_seconds": float(metadata_frame["runtime_seconds"].max()),
        "minimum_support": config.minimum_support,
        "minimum_support_count_per_sample": math.ceil(config.minimum_support * prepared.transaction_count),
        "maximum_length": config.maximum_length,
        "candidate_rules_evaluated": len(candidates),
        "very_stable_rules": int((stability.stability_category == "Very stable").sum()),
        "moderately_stable_rules": int((stability.stability_category == "Moderately stable").sum()),
        "weakly_stable_rules": int((stability.stability_category == "Weakly stable").sum()),
        "unstable_rules": int((stability.stability_category == "Unstable").sum()),
        "seeds": " | ".join(str(seed) for seed in metadata_frame["seed"]),
        "expansion_decision": (
            "Expanded because all frozen criteria passed."
            if expanded
            else "Stopped at 20 because the frozen expansion criteria did not all pass."
        ),
    }
    save_csv(
        pd.DataFrame([summary]),
        project_path("outputs", "tables", "bootstrap_summary.csv"),
    )
    return summary


if __name__ == "__main__":
    print(run_bootstrap_experiment())
