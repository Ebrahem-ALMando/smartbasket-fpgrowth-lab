"""Matched random-subset scalability protocols correcting the Phase 4 diagnostic."""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd

from src.data.export import save_csv
from src.data.paths import project_path
from src.mining.apriori_runner import run_apriori
from src.mining.basket_loader import load_prepared_basket
from src.mining.fpgrowth_runner import run_fpgrowth


FRACTIONS = (0.25, 0.50, 0.75, 1.00)
SUBSET_SEEDS = (5501, 5502, 5503)
FULL_SUPPORT_COUNT = 90


def protocol_support(
    protocol: str,
    transaction_count: int,
    *,
    fixed_proportion: float = 0.005,
    fixed_count: int = FULL_SUPPORT_COUNT,
) -> tuple[float, int]:
    """Return the declared support proportion and count for a protocol."""
    if transaction_count < 1:
        raise ValueError("transaction_count must be positive")
    if protocol == "A_fixed_support_proportion":
        return fixed_proportion, math.ceil(fixed_proportion * transaction_count)
    if protocol == "B_fixed_absolute_support_count":
        if fixed_count > transaction_count:
            raise ValueError("fixed support count exceeds subset transaction count")
        return fixed_count / transaction_count, fixed_count
    raise ValueError(f"Unknown scalability protocol: {protocol}")


def deterministic_subset_indices(
    total_transactions: int, fraction: float, seed: int
) -> np.ndarray:
    """Choose a reproducible subset without replacement and return sorted rows."""
    size = int(math.floor(total_transactions * fraction))
    if not 0 < size <= total_transactions:
        raise ValueError("fraction creates an invalid subset size")
    if size == total_transactions:
        return np.arange(total_transactions, dtype=np.int64)
    indices = np.random.default_rng(seed).choice(
        total_transactions, size=size, replace=False
    )
    return np.sort(indices.astype(np.int64, copy=False))


def run_corrected_scalability() -> dict[str, object]:
    """Run both algorithms on identical subsets under both support protocols."""
    prepared = load_prepared_basket()
    records: list[dict[str, object]] = []
    output_path = project_path(
        "outputs", "comparisons", "scalability_corrected_runs.csv"
    )
    for fraction in FRACTIONS:
        seeds = (0,) if fraction == 1.0 else SUBSET_SEEDS
        for seed in seeds:
            indices = deterministic_subset_indices(
                prepared.transaction_count, fraction, seed
            )
            subset_matrix = prepared.matrix[indices]
            subset = pd.DataFrame.sparse.from_spmatrix(
                subset_matrix.astype(bool, copy=False),
                columns=list(prepared.product_codes),
            )
            active_products = int(np.count_nonzero(np.asarray(subset_matrix.sum(axis=0))))
            checksum = hashlib.sha256(indices.tobytes()).hexdigest()
            for protocol in (
                "A_fixed_support_proportion",
                "B_fixed_absolute_support_count",
            ):
                minimum_support, minimum_count = protocol_support(
                    protocol, len(indices)
                )
                for algorithm, operation in (
                    ("FP-Growth", run_fpgrowth),
                    ("Apriori", run_apriori),
                ):
                    base = {
                        "protocol": protocol,
                        "subset_fraction": fraction,
                        "seed": seed,
                        "transaction_count": len(indices),
                        "active_product_count": active_products,
                        "subset_index_sha256": checksum,
                        "minimum_support": minimum_support,
                        "minimum_support_count": minimum_count,
                        "algorithm": algorithm,
                        "maximum_length": 3,
                        "status": "failed",
                        "failure_reason": "",
                    }
                    try:
                        run = operation(
                            subset,
                            minimum_support=minimum_support,
                            maximum_length=3,
                        )
                        lengths = run.itemsets.itemsets.map(len).value_counts()
                        base.update(
                            {
                                "status": "success",
                                "runtime_seconds": run.benchmark.runtime_seconds,
                                "frequent_itemset_count": len(run.itemsets),
                                "length_1_count": int(lengths.get(1, 0)),
                                "length_2_count": int(lengths.get(2, 0)),
                                "length_3_count": int(lengths.get(3, 0)),
                                "rss_before_bytes": run.benchmark.rss_before_bytes,
                                "rss_after_bytes": run.benchmark.rss_after_bytes,
                                "approximate_rss_delta_bytes": run.benchmark.rss_delta_bytes,
                                "memory_measurement": run.benchmark.memory_measurement,
                            }
                        )
                    except Exception as exc:
                        base["failure_reason"] = f"{type(exc).__name__}: {exc}"
                    records.append(base)
                    save_csv(pd.DataFrame(records), output_path)

    runs = pd.DataFrame(records)
    successful = runs[runs.status.eq("success")]
    summary = (
        successful.groupby(
            ["protocol", "subset_fraction", "transaction_count", "algorithm"],
            as_index=False,
        )
        .agg(
            seeds_completed=("seed", "size"),
            support_proportion=("minimum_support", "first"),
            support_count=("minimum_support_count", "first"),
            median_runtime_seconds=("runtime_seconds", "median"),
            minimum_runtime_seconds=("runtime_seconds", "min"),
            maximum_runtime_seconds=("runtime_seconds", "max"),
            median_itemset_count=("frequent_itemset_count", "median"),
            minimum_itemset_count=("frequent_itemset_count", "min"),
            maximum_itemset_count=("frequent_itemset_count", "max"),
            median_approximate_rss_delta_bytes=(
                "approximate_rss_delta_bytes",
                "median",
            ),
        )
        .sort_values(["protocol", "subset_fraction", "algorithm"])
    )
    save_csv(
        summary,
        project_path("outputs", "comparisons", "scalability_protocol_summary.csv"),
    )

    original = pd.read_csv(
        project_path("outputs", "comparisons", "scalability_experiment.csv")
    )
    original_comparison = pd.DataFrame(
        {
            "source": "Phase 4 deterministic time prefix",
            "protocol": "A_fixed_support_proportion",
            "subset_fraction": original["transaction_fraction"],
            "algorithm": original["algorithm"],
            "support_proportion": original["minimum_support"],
            "support_count": original["minimum_support_count"],
            "runtime_seconds": original["runtime_seconds"],
            "itemset_count": original["frequent_itemset_count"],
            "aggregation": "single time-prefix run",
        }
    )
    corrected_comparison = summary.rename(
        columns={
            "median_runtime_seconds": "runtime_seconds",
            "median_itemset_count": "itemset_count",
        }
    )[[
        "protocol",
        "subset_fraction",
        "algorithm",
        "support_proportion",
        "support_count",
        "runtime_seconds",
        "itemset_count",
    ]]
    corrected_comparison.insert(0, "source", "Phase 5 deterministic random subsets")
    corrected_comparison["aggregation"] = "median across seeds below 100%"
    combined = pd.concat([original_comparison, corrected_comparison], ignore_index=True)
    save_csv(
        combined,
        project_path(
            "outputs", "comparisons", "scalability_original_vs_corrected.csv"
        ),
    )
    return {
        "run_count": len(runs),
        "successful_runs": int(runs.status.eq("success").sum()),
        "failed_runs": int((~runs.status.eq("success")).sum()),
        "fractions": FRACTIONS,
        "subset_seeds": SUBSET_SEEDS,
        "protocols": 2,
    }


if __name__ == "__main__":
    print(run_corrected_scalability())
