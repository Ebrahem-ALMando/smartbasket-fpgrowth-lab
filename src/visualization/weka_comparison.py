"""Evidence-driven Python versus WEKA comparison figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.weka.weka_metrics import METRIC_TOLERANCES


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _bar(labels: list[str], values: list[float], title: str, ylabel: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color=["#2f7d6d", "#d98c3f", "#8b5fbf", "#4c78a8"][: len(labels)])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.4g}", ha="center", va="bottom")
    _save(fig, path)


def _difference_distribution(differences: pd.DataFrame, metric: str, path: Path) -> None:
    subset = differences.loc[differences["metric"] == metric, "absolute_difference"].dropna().astype(float)
    fig, ax = plt.subplots(figsize=(8, 5))
    if subset.empty:
        ax.text(0.5, 0.5, "No common rules / لا توجد قواعد مشتركة", ha="center", va="center")
    elif (subset == 0).all():
        ax.bar(["Exact zero difference"], [len(subset)], color="#2f7d6d")
        ax.set_ylabel("Rule count / عدد القواعد")
    else:
        positive = subset[subset > 0]
        bins = min(40, max(10, int(np.sqrt(len(subset)))))
        ax.hist(positive, bins=bins, color="#4c78a8", alpha=0.85)
        tolerance = METRIC_TOLERANCES[metric].absolute
        ax.axvline(tolerance, color="#d62728", linestyle="--", label=f"Tolerance = {tolerance:g}")
        ax.set_xscale("log")
        ax.legend()
        ax.set_xlabel(f"Absolute {metric} difference / الفرق المطلق")
    ax.set_title(f"{metric.title()} difference distribution / توزيع الفروق")
    ax.grid(axis="y", alpha=0.25)
    _save(fig, path)


def generate_weka_comparison_figures(
    audit: pd.DataFrame,
    differences: pd.DataFrame,
    runtime_summary: pd.DataFrame,
    parameter_alignment: pd.DataFrame,
    output_directory: Path,
) -> list[Path]:
    """Generate the ten required figures from actual comparison outputs."""
    output_directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    counts = audit["presence_status"].value_counts()
    path = output_directory / "python_weka_rule_overlap_summary.png"
    _bar(["Common", "Python only", "WEKA only"],
         [counts.get("common", 0), counts.get("python_only", 0), counts.get("weka_only", 0)],
         "Python–WEKA rule overlap / تداخل القواعد", "Rule count / عدد القواعد", path)
    paths.append(path)
    for metric in ("support", "confidence", "lift"):
        path = output_directory / f"python_weka_{metric}_difference_distribution.png"
        _difference_distribution(differences, metric, path)
        paths.append(path)

    maxima = differences.groupby("metric")["absolute_difference"].max().reindex(
        ["support", "confidence", "lift", "leverage", "conviction"]
    ).fillna(0)
    path = output_directory / "python_weka_maximum_metric_differences.png"
    _bar([name.title() for name in maxima.index], maxima.tolist(),
         "Maximum absolute metric differences / أكبر فرق مطلق", "Absolute difference", path)
    paths.append(path)

    path = output_directory / "python_only_vs_weka_only_rule_counts.png"
    _bar(["Python only", "WEKA only"], [counts.get("python_only", 0), counts.get("weka_only", 0)],
         "Unmatched logical rules / القواعد غير المتطابقة", "Rule count", path)
    paths.append(path)

    ordered_runtime = runtime_summary.set_index("implementation").reindex(["Python", "WEKA"])
    path = output_directory / "python_weka_mining_runtime.png"
    _bar([str(v) for v in ordered_runtime.index], ordered_runtime["median_mining_seconds"].fillna(0).tolist(),
         "Median mining runtime / زمن التعدين الوسيط", "Seconds", path)
    paths.append(path)
    path = output_directory / "python_weka_end_to_end_runtime.png"
    _bar([str(v) for v in ordered_runtime.index], ordered_runtime["median_end_to_end_seconds"].fillna(0).tolist(),
         "Median end-to-end runtime / الزمن الكلي الوسيط", "Seconds", path)
    paths.append(path)

    common = audit.loc[audit["presence_status"] == "common"].copy()
    path = output_directory / "python_weka_rule_order_difference.png"
    fig, ax = plt.subplots(figsize=(7, 6))
    if common.empty:
        ax.text(0.5, 0.5, "No common rules", ha="center")
    else:
        ax.scatter(common["python_source_rank"], common["weka_source_rank"], s=10, alpha=0.35, color="#4c78a8")
        maximum = max(common["python_source_rank"].max(), common["weka_source_rank"].max())
        ax.plot([1, maximum], [1, maximum], linestyle="--", color="#d62728", label="Identical rank")
        ax.set_xlabel("Python source rank")
        ax.set_ylabel("WEKA source rank")
        ax.legend()
    ax.set_title("Rule ordering is separate from identity / ترتيب القواعد")
    ax.grid(alpha=0.2)
    _save(fig, path)
    paths.append(path)

    status_counts = parameter_alignment["alignment_status"].value_counts()
    path = output_directory / "python_weka_parameter_alignment_summary.png"
    _bar(status_counts.index.astype(str).tolist(), status_counts.astype(float).tolist(),
         "Parameter alignment status / محاذاة المعاملات", "Parameter count", path)
    paths.append(path)
    return paths
