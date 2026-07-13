"""Resource-conscious mlxtend Apriori execution using shared settings."""

from __future__ import annotations

import pandas as pd
from mlxtend.frequent_patterns import apriori

from src.evaluation.mining_benchmark import measure_call
from src.mining.fpgrowth_runner import FrequentPatternRun


def run_apriori(
    basket: pd.DataFrame,
    *,
    minimum_support: float,
    maximum_length: int | None,
    low_memory: bool = True,
) -> FrequentPatternRun:
    """Run Apriori without changing the shared support or length settings."""
    if not 0 < minimum_support <= 1:
        raise ValueError("minimum_support must be within (0, 1]")
    measured = measure_call(
        "Apriori",
        lambda: apriori(
            basket,
            min_support=minimum_support,
            use_colnames=True,
            max_len=maximum_length,
            low_memory=low_memory,
            verbose=0,
        ),
    )
    if measured.value is None:
        raise RuntimeError(
            f"Apriori failed: {measured.benchmark.error_type}: "
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
