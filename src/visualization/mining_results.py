"""Publication-quality Phase 4 mining and benchmark figures."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.paths import ensure_directory


FIGURE_DPI = 300


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


def _short_itemset(serialized_descriptions: str, width: int = 58) -> str:
    labels = json.loads(serialized_descriptions)
    text = " + ".join(label.split(" — ", 1)[-1] for label in labels)
    return text if len(text) <= width else text[: width - 1] + "…"


def generate_fpgrowth_figures(
    sweep: pd.DataFrame,
    frequent_itemsets: pd.DataFrame,
    rules: pd.DataFrame,
) -> list[Path]:
    """Generate threshold, itemset, and association-rule figures."""
    output = ensure_directory("outputs", "figures")
    successful = sweep[sweep["execution_status"].str.startswith("success")].copy()
    successful = successful.sort_values("minimum_support")
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        successful["minimum_support"] * 100,
        successful["frequent_itemset_count"],
        marker="o",
        color="#2563eb",
    )
    ax.set_xlabel("Minimum Support (%)")
    ax.set_ylabel("Frequent itemsets")
    ax.set_title("Minimum Support vs Frequent Itemsets (linear axes)")
    ax.grid(alpha=0.25)
    path = output / "minimum_support_vs_frequent_itemsets.png"
    _save(fig, path)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        successful["minimum_support"] * 100,
        successful["runtime_seconds"],
        marker="o",
        color="#7c3aed",
    )
    ax.set_xlabel("Minimum Support (%)")
    ax.set_ylabel("FP-Growth wall-clock runtime (seconds)")
    ax.set_title("Minimum Support vs FP-Growth Runtime (linear axes)")
    ax.grid(alpha=0.25)
    path = output / "minimum_support_vs_runtime.png"
    _save(fig, path)
    paths.append(path)

    length_counts = frequent_itemsets["itemset_length"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(length_counts.index.astype(str), length_counts.values, color="#0f766e")
    ax.set_xlabel("Itemset length")
    ax.set_ylabel("Frequent itemsets")
    ax.set_title("Final Frequent Itemsets by Length (linear axes)")
    ax.bar_label(ax.containers[0], fmt="%d", padding=3)
    path = output / "frequent_itemsets_by_length.png"
    _save(fig, path)
    paths.append(path)

    top = frequent_itemsets.nlargest(15, "support").sort_values("support")
    labels = top["product_descriptions"].map(_short_itemset)
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(labels, top["support"] * 100, color="#0284c7")
    ax.set_xlabel("Support (% of UK transactions)")
    ax.set_title("Top Frequent Itemsets by Support (linear axes)")
    path = output / "top_frequent_itemsets_by_support.png"
    _save(fig, path)
    paths.append(path)

    finite_rules = rules.loc[
        np.isfinite(rules["support"])
        & np.isfinite(rules["confidence"])
        & np.isfinite(rules["lift"])
    ]
    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(
        finite_rules["support"] * 100,
        finite_rules["confidence"] * 100,
        c=finite_rules["lift"],
        cmap="viridis",
        s=10,
        alpha=0.55,
    )
    fig.colorbar(scatter, ax=ax, label="Lift")
    ax.set_xlabel("Rule Support (%)")
    ax.set_ylabel("Confidence (%)")
    ax.set_title("Association Rules: Support vs Confidence (linear axes)")
    ax.grid(alpha=0.2)
    path = output / "association_rule_support_vs_confidence.png"
    _save(fig, path)
    paths.append(path)

    lift_limit = float(finite_rules["lift"].quantile(0.99))
    shown_lift = finite_rules.loc[finite_rules["lift"] <= lift_limit, "lift"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(shown_lift, bins=50, color="#d97706", edgecolor="white")
    ax.axvline(1.0, color="#991b1b", linestyle="--", label="Independence baseline")
    ax.set_xlabel("Lift")
    ax.set_ylabel("Rules")
    ax.set_title("Lift Distribution (linear axes; displayed through 99th percentile)")
    ax.legend()
    path = output / "association_rule_lift_distribution.png"
    _save(fig, path)
    paths.append(path)
    return paths


def generate_comparison_figures(
    benchmark: pd.DataFrame,
    scalability: pd.DataFrame,
    equivalence_summary: dict[str, object],
) -> list[Path]:
    """Generate fair runtime, scalability, and equivalence figures."""
    output = ensure_directory("outputs", "figures")
    paths: list[Path] = []
    measured = benchmark.loc[benchmark["run_type"].eq("measured")]
    medians = measured.groupby("algorithm")["runtime_seconds"].median().sort_index()
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(medians.index, medians.values, color=["#7c3aed", "#2563eb"])
    ax.set_ylabel("Median wall-clock runtime (seconds)")
    ax.set_title("FP-Growth vs Apriori Runtime (linear axis; 3 measured runs)")
    ax.bar_label(ax.containers[0], fmt="%.2f s", padding=3)
    path = output / "fpgrowth_vs_apriori_runtime.png"
    _save(fig, path)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8, 5))
    for algorithm, group in scalability.groupby("algorithm"):
        ordered = group.sort_values("transaction_count")
        ax.plot(
            ordered["transaction_count"],
            ordered["runtime_seconds"],
            marker="o",
            label=algorithm,
        )
    ax.set_xlabel("Transactions (deterministic Phase 3 row prefix)")
    ax.set_ylabel("Wall-clock runtime (seconds)")
    ax.set_title("Controlled Scalability Comparison (linear axes; one run per point)")
    ax.legend()
    ax.grid(alpha=0.25)
    path = output / "scalability_fpgrowth_vs_apriori.png"
    _save(fig, path)
    paths.append(path)

    labels = ["Common", "FP-Growth only", "Apriori only"]
    values = [
        int(equivalence_summary["common_itemsets"]),
        int(equivalence_summary["fpgrowth_only_itemsets"]),
        int(equivalence_summary["apriori_only_itemsets"]),
    ]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(labels, values, color=["#16a34a", "#dc2626", "#dc2626"])
    ax.set_ylabel("Itemsets")
    ax.set_title("Frequent-Itemset Equivalence (linear axis)")
    ax.bar_label(ax.containers[0], fmt="%d", padding=3)
    path = output / "itemset_equivalence_summary.png"
    _save(fig, path)
    paths.append(path)
    return paths
