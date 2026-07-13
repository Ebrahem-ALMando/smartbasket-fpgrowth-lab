"""Reproducible Phase 4 FP-Growth, rule, and Apriori experiment pipelines."""

from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass
from importlib.metadata import version
from statistics import median

import numpy as np
import pandas as pd

from src.data.export import save_csv, save_json
from src.data.paths import project_path
from src.evaluation.itemset_equivalence import compare_itemsets
from src.mining.apriori_runner import run_apriori
from src.mining.basket_loader import load_prepared_basket
from src.mining.fpgrowth_runner import FrequentPatternRun, run_fpgrowth
from src.mining.itemset_utils import canonicalize_frequent_itemsets
from src.mining.rule_generation import generate_rules, select_rules
from src.mining.threshold_selection import (
    ResourceSafeguards,
    run_threshold_sweep,
    select_final_confidence,
    select_final_support,
)
from src.visualization.mining_results import (
    generate_comparison_figures,
    generate_fpgrowth_figures,
)


FINAL_LIFT_THRESHOLD = 1.20
FINAL_MAXIMUM_LENGTH = 3
BENCHMARK_REPEATS = 3
SCALABILITY_FRACTIONS = (0.25, 0.50, 0.75, 1.00)


@dataclass(frozen=True)
class FPGrowthExperimentSummary:
    minimum_support: float
    minimum_support_count: int
    minimum_confidence: float
    minimum_lift: float
    maximum_length: int
    frequent_itemset_count: int
    all_rule_count: int
    selected_rule_count: int
    runtime_seconds: float


@dataclass(frozen=True)
class ComparisonExperimentSummary:
    fpgrowth_median_runtime_seconds: float
    apriori_median_runtime_seconds: float
    equivalent: bool
    common_itemsets: int
    maximum_support_difference: float


def _metric_summary(rules: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in [
        "antecedent_support",
        "consequent_support",
        "support",
        "confidence",
        "lift",
        "leverage",
        "conviction",
    ]:
        values = rules[metric].astype(float)
        finite = values[np.isfinite(values)]
        rows.append(
            {
                "metric": metric,
                "total_count": len(values),
                "finite_count": len(finite),
                "infinite_count": int(np.isinf(values).sum()),
                "missing_count": int(values.isna().sum()),
                "minimum": float(finite.min()) if len(finite) else np.nan,
                "median": float(finite.median()) if len(finite) else np.nan,
                "mean": float(finite.mean()) if len(finite) else np.nan,
                "maximum": float(finite.max()) if len(finite) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _save_rule_outputs(rules: pd.DataFrame, selected: pd.DataFrame) -> None:
    table = lambda name: project_path("outputs", "tables", name)
    save_csv(rules, table("association_rules_all.csv"))
    save_csv(selected, table("association_rules_selected.csv"))
    source = selected if not selected.empty else rules
    save_csv(
        source.sort_values(
            ["support", "confidence", "lift", "rule_key"],
            ascending=[False, False, False, True],
            kind="mergesort",
        ).head(50),
        table("top_rules_by_support.csv"),
    )
    save_csv(
        source.sort_values(
            ["confidence", "lift", "support", "rule_key"],
            ascending=[False, False, False, True],
            kind="mergesort",
        ).head(50),
        table("top_rules_by_confidence.csv"),
    )
    save_csv(
        source.sort_values(
            ["lift", "confidence", "support", "rule_key"],
            ascending=[False, False, False, True],
            kind="mergesort",
        ).head(50),
        table("top_rules_by_lift.csv"),
    )
    save_csv(_metric_summary(rules), table("rule_metric_summary.csv"))
    length_summary = (
        rules.assign(total_rule_length=rules.antecedent_length + rules.consequent_length)
        .groupby(["antecedent_length", "consequent_length", "total_rule_length"], as_index=False)
        .agg(rule_count=("rule_key", "size"))
        .sort_values(["total_rule_length", "antecedent_length"])
    )
    save_csv(length_summary, table("rule_length_summary.csv"))


def run_fpgrowth_experiment() -> FPGrowthExperimentSummary:
    """Run the guarded sweep, final FP-Growth, and association-rule analysis."""
    prepared = load_prepared_basket()
    basket = prepared.to_sparse_boolean_frame()
    sweep = run_threshold_sweep(
        basket,
        transaction_count=prepared.transaction_count,
        descriptions=prepared.descriptions,
        maximum_length=FINAL_MAXIMUM_LENGTH,
    )
    final_row = select_final_support(sweep)
    minimum_support = float(final_row["minimum_support"])
    minimum_support_count = int(final_row["minimum_support_count"])
    minimum_confidence = select_final_confidence(final_row)
    save_csv(
        sweep, project_path("outputs", "tables", "fpgrowth_threshold_sweep.csv")
    )

    final_run = run_fpgrowth(
        basket,
        minimum_support=minimum_support,
        maximum_length=FINAL_MAXIMUM_LENGTH,
    )
    canonical = canonicalize_frequent_itemsets(
        final_run.itemsets,
        transaction_count=prepared.transaction_count,
        descriptions=prepared.descriptions,
    )
    if not np.allclose(
        canonical["support_count"],
        np.rint(canonical["support"] * prepared.transaction_count),
        atol=0,
    ):
        raise AssertionError("Support counts do not reconcile with proportions")
    save_csv(
        canonical,
        project_path("outputs", "tables", "frequent_itemsets_fpgrowth.csv"),
    )
    length_summary = (
        canonical.groupby("itemset_length", as_index=False)
        .agg(
            frequent_itemset_count=("itemset_key", "size"),
            minimum_support=("support", "min"),
            maximum_support=("support", "max"),
            minimum_support_count=("support_count", "min"),
            maximum_support_count=("support_count", "max"),
        )
        .sort_values("itemset_length")
    )
    save_csv(
        length_summary,
        project_path("outputs", "tables", "frequent_itemsets_length_summary.csv"),
    )

    rules = generate_rules(
        final_run.itemsets,
        transaction_count=prepared.transaction_count,
        descriptions=prepared.descriptions,
        minimum_confidence=0.0,
    )
    selected = select_rules(
        rules,
        minimum_support=minimum_support,
        minimum_support_count=minimum_support_count,
        minimum_confidence=minimum_confidence,
        minimum_lift=FINAL_LIFT_THRESHOLD,
    )
    _save_rule_outputs(rules, selected)
    metadata = {
        "algorithm": "mlxtend.frequent_patterns.fpgrowth",
        "scope": "United Kingdom",
        "transaction_count": prepared.transaction_count,
        "product_count": prepared.product_count,
        "minimum_support": minimum_support,
        "minimum_support_count": minimum_support_count,
        "minimum_confidence": minimum_confidence,
        "interpretation_minimum_lift": FINAL_LIFT_THRESHOLD,
        "maximum_itemset_length": FINAL_MAXIMUM_LENGTH,
        "maximum_length_limitation": "Itemsets of length four or greater were not mined.",
        "frequent_itemset_count": len(canonical),
        "itemset_length_distribution": {
            str(int(row.itemset_length)): int(row.frequent_itemset_count)
            for row in length_summary.itertuples(index=False)
        },
        "association_rule_count": len(rules),
        "selected_rule_count": len(selected),
        "runtime_seconds": final_run.benchmark.runtime_seconds,
        "approximate_rss_before_bytes": final_run.benchmark.rss_before_bytes,
        "approximate_rss_after_bytes": final_run.benchmark.rss_after_bytes,
        "approximate_rss_delta_bytes": final_run.benchmark.rss_delta_bytes,
        "memory_measurement": final_run.benchmark.memory_measurement,
        "threshold_selection": (
            "Lowest successful sweep threshold with length-2 and length-3 itemsets, "
            "manageable rules, and runtime/memory below frozen soft safeguards."
        ),
        "resource_safeguards": asdict(ResourceSafeguards()),
        "environment": {
            "python": platform.python_version(),
            "pandas": version("pandas"),
            "scipy": version("scipy"),
            "mlxtend": version("mlxtend"),
        },
    }
    save_json(
        metadata,
        project_path("outputs", "tables", "fpgrowth_run_metadata.json"),
    )
    generate_fpgrowth_figures(sweep, canonical, rules)
    return FPGrowthExperimentSummary(
        minimum_support=minimum_support,
        minimum_support_count=minimum_support_count,
        minimum_confidence=minimum_confidence,
        minimum_lift=FINAL_LIFT_THRESHOLD,
        maximum_length=FINAL_MAXIMUM_LENGTH,
        frequent_itemset_count=len(canonical),
        all_rule_count=len(rules),
        selected_rule_count=len(selected),
        runtime_seconds=final_run.benchmark.runtime_seconds,
    )


def _benchmark_row(
    run: FrequentPatternRun,
    *,
    run_type: str,
    run_index: int,
    transaction_count: int,
    product_count: int,
    minimum_support: float,
) -> dict[str, object]:
    return {
        "algorithm": run.benchmark.algorithm,
        "run_type": run_type,
        "run_index": run_index,
        "status": run.benchmark.status,
        "transaction_count": transaction_count,
        "product_count": product_count,
        "minimum_support": minimum_support,
        "minimum_support_count": int(np.ceil(minimum_support * transaction_count)),
        "maximum_length": run.maximum_length,
        "frequent_itemset_count": len(run.itemsets),
        "runtime_seconds": run.benchmark.runtime_seconds,
        "rss_before_bytes": run.benchmark.rss_before_bytes,
        "rss_after_bytes": run.benchmark.rss_after_bytes,
        "approximate_rss_delta_bytes": run.benchmark.rss_delta_bytes,
        "memory_measurement": run.benchmark.memory_measurement,
    }


def run_comparison_experiment() -> ComparisonExperimentSummary:
    """Run fair full-data repeated benchmarks, equivalence, and scalability."""
    prepared = load_prepared_basket()
    basket = prepared.to_sparse_boolean_frame()
    metadata = json.loads(
        project_path("outputs", "tables", "fpgrowth_run_metadata.json").read_text(
            encoding="utf-8"
        )
    )
    minimum_support = float(metadata["minimum_support"])
    maximum_length = int(metadata["maximum_itemset_length"])

    fpgrowth_warmup = run_fpgrowth(
        basket, minimum_support=minimum_support, maximum_length=maximum_length
    )
    apriori_warmup = run_apriori(
        basket, minimum_support=minimum_support, maximum_length=maximum_length
    )
    comparison, equivalence = compare_itemsets(
        fpgrowth_warmup.itemsets, apriori_warmup.itemsets, absolute_tolerance=1e-12
    )
    save_csv(
        comparison,
        project_path("outputs", "comparisons", "itemset_equivalence.csv"),
    )
    save_json(
        equivalence.as_dict(),
        project_path(
            "outputs", "comparisons", "itemset_equivalence_summary.json"
        ),
    )

    benchmark_rows = [
        _benchmark_row(
            fpgrowth_warmup,
            run_type="warmup",
            run_index=0,
            transaction_count=prepared.transaction_count,
            product_count=prepared.product_count,
            minimum_support=minimum_support,
        ),
        _benchmark_row(
            apriori_warmup,
            run_type="warmup",
            run_index=0,
            transaction_count=prepared.transaction_count,
            product_count=prepared.product_count,
            minimum_support=minimum_support,
        ),
    ]
    for index in range(1, BENCHMARK_REPEATS + 1):
        for operation in (run_fpgrowth, run_apriori):
            run = operation(
                basket,
                minimum_support=minimum_support,
                maximum_length=maximum_length,
            )
            benchmark_rows.append(
                _benchmark_row(
                    run,
                    run_type="measured",
                    run_index=index,
                    transaction_count=prepared.transaction_count,
                    product_count=prepared.product_count,
                    minimum_support=minimum_support,
                )
            )
    benchmark = pd.DataFrame(benchmark_rows)
    save_csv(
        benchmark,
        project_path(
            "outputs", "comparisons", "fpgrowth_apriori_benchmark.csv"
        ),
    )

    scalability_rows = []
    for fraction in SCALABILITY_FRACTIONS:
        rows = max(1, int(np.floor(prepared.transaction_count * fraction)))
        subset = basket.iloc[:rows]
        for operation in (run_fpgrowth, run_apriori):
            run = operation(
                subset,
                minimum_support=minimum_support,
                maximum_length=maximum_length,
            )
            record = _benchmark_row(
                run,
                run_type="scalability",
                run_index=1,
                transaction_count=rows,
                product_count=prepared.product_count,
                minimum_support=minimum_support,
            )
            record["transaction_fraction"] = fraction
            record["subset_method"] = (
                "Deterministic prefix of the stable Phase 3 transaction index"
            )
            scalability_rows.append(record)
    scalability = pd.DataFrame(scalability_rows)
    save_csv(
        scalability,
        project_path("outputs", "comparisons", "scalability_experiment.csv"),
    )
    generate_comparison_figures(benchmark, scalability, equivalence.as_dict())

    measured = benchmark[benchmark["run_type"].eq("measured")]
    fp_median = median(
        measured.loc[measured.algorithm.eq("FP-Growth"), "runtime_seconds"]
    )
    apriori_median = median(
        measured.loc[measured.algorithm.eq("Apriori"), "runtime_seconds"]
    )
    return ComparisonExperimentSummary(
        fpgrowth_median_runtime_seconds=fp_median,
        apriori_median_runtime_seconds=apriori_median,
        equivalent=equivalence.equivalent,
        common_itemsets=equivalence.common_itemsets,
        maximum_support_difference=equivalence.maximum_support_difference,
    )


if __name__ == "__main__":
    from src.mining.fp_tree_steps import generate_educational_outputs

    print(generate_educational_outputs())
    print(run_fpgrowth_experiment())
    print(run_comparison_experiment())
