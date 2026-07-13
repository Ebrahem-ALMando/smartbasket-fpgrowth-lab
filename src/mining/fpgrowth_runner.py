"""Explicit, benchmarked mlxtend FP-Growth execution."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from mlxtend.frequent_patterns import fpgrowth

from src.evaluation.mining_benchmark import BenchmarkRecord, measure_call


@dataclass(frozen=True)
class FrequentPatternRun:
    """Frequent itemsets plus parameters and benchmark evidence."""

    itemsets: pd.DataFrame
    benchmark: BenchmarkRecord
    minimum_support: float
    maximum_length: int | None


def run_fpgrowth(
    basket: pd.DataFrame,
    *,
    minimum_support: float,
    maximum_length: int | None,
) -> FrequentPatternRun:
    """Run FP-Growth with no silent support or length changes."""
    if not 0 < minimum_support <= 1:
        raise ValueError("minimum_support must be within (0, 1]")
    measured = measure_call(
        "FP-Growth",
        lambda: fpgrowth(
            basket,
            min_support=minimum_support,
            use_colnames=True,
            max_len=maximum_length,
            verbose=0,
        ),
    )
    if measured.value is None:
        raise RuntimeError(
            f"FP-Growth failed: {measured.benchmark.error_type}: "
            f"{measured.benchmark.error_message}"
        )
    itemsets = measured.value.sort_values(
        "support", ascending=False, kind="mergesort"
    ).reset_index(drop=True)
    return FrequentPatternRun(
        itemsets=itemsets,
        benchmark=measured.benchmark,
        minimum_support=minimum_support,
        maximum_length=maximum_length,
    )
