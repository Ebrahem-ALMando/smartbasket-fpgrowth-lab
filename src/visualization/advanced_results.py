"""Publication-quality Phase 5 stability, quality, scalability, and action figures."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.paths import project_path


DPI = 300


def _save(fig: plt.Figure, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(
        project_path("outputs", "figures", filename),
        dpi=DPI,
        bbox_inches="tight",
    )
    plt.close(fig)


def generate_advanced_figures() -> list[str]:
    """Generate all required non-network Phase 5 figures from saved results."""
    stability = pd.read_csv(project_path("outputs", "tables", "rule_stability_results.csv"))
    categories = pd.read_csv(project_path("outputs", "tables", "rule_stability_categories.csv"))
    quality = pd.read_csv(project_path("outputs", "tables", "rule_quality_audit.csv"))
    flags = pd.read_csv(project_path("outputs", "tables", "misleading_rule_flags.csv"))
    tiers = pd.read_csv(project_path("outputs", "tables", "rule_evidence_tiers.csv"))
    redundant = pd.read_csv(project_path("outputs", "tables", "redundant_rules.csv"))
    scalability = pd.read_csv(project_path("outputs", "comparisons", "scalability_protocol_summary.csv"))
    original_corrected = pd.read_csv(project_path("outputs", "comparisons", "scalability_original_vs_corrected.csv"))
    actions = pd.read_csv(project_path("outputs", "tables", "business_action_summary.csv"))
    created: list[str] = []

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(categories.stability_category, categories.rule_count, color=["#16a34a", "#65a30d", "#f59e0b", "#dc2626"])
    ax.set_ylabel("Phase 4 candidate rules")
    ax.set_title("Bootstrap Stability Categories (20 transaction-level resamples)")
    ax.tick_params(axis="x", rotation=15)
    ax.bar_label(ax.containers[0], fmt="%d", padding=3)
    _save(fig, "rule_stability_category_distribution.png"); created.append("rule_stability_category_distribution.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(stability.rule_presence_rate, bins=np.linspace(0, 1, 21), color="#0284c7", edgecolor="white")
    for value in [0.2, 0.5, 0.8]: ax.axvline(value, color="#334155", linestyle="--", alpha=0.6)
    ax.set_xlabel("Bootstrap rule-presence rate")
    ax.set_ylabel("Rules")
    ax.set_title("Bootstrap Presence-Rate Distribution (20 resamples)")
    _save(fig, "bootstrap_presence_rate_distribution.png"); created.append("bootstrap_presence_rate_distribution.png")

    top = stability[stability.stability_category.eq("Very stable")].nlargest(12, "support_count").sort_values("confidence_mean")
    fig, ax = plt.subplots(figsize=(10, 7))
    xerr = np.vstack([top.confidence_mean-top.confidence_p025, top.confidence_p975-top.confidence_mean])
    ax.errorbar(top.confidence_mean, top.rule_key, xerr=xerr, fmt="o", color="#7c3aed", ecolor="#c4b5fd", capsize=3)
    ax.set_xlabel("Bootstrap mean Confidence and empirical 2.5%–97.5% interval")
    ax.set_title("Confidence Uncertainty for High-Support Very Stable Rules")
    _save(fig, "confidence_uncertainty_top_stable_rules.png"); created.append("confidence_uncertainty_top_stable_rules.png")

    top_lift = stability[stability.stability_category.eq("Very stable")].nlargest(12, "support_count").sort_values("lift_mean")
    fig, ax = plt.subplots(figsize=(10, 7))
    xerr = np.vstack([top_lift.lift_mean-top_lift.lift_p025, top_lift.lift_p975-top_lift.lift_mean])
    ax.errorbar(top_lift.lift_mean, top_lift.rule_key, xerr=xerr, fmt="o", color="#d97706", ecolor="#fed7aa", capsize=3)
    ax.set_xlabel("Bootstrap mean Lift and empirical 2.5%–97.5% interval")
    ax.set_title("Lift Uncertainty for High-Support Very Stable Rules")
    _save(fig, "lift_uncertainty_top_stable_rules.png"); created.append("lift_uncertainty_top_stable_rules.png")

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(quality.support_count, quality.rule_presence_rate, s=12, alpha=0.45, c=quality.confidence, cmap="viridis")
    ax.axvline(90, color="#dc2626", linestyle="--", label="Minimum count 90")
    ax.set_xlabel("Original support count")
    ax.set_ylabel("Bootstrap presence rate")
    ax.set_title("Rule Support Count vs Bootstrap Stability")
    ax.legend()
    _save(fig, "support_vs_stability.png"); created.append("support_vs_stability.png")

    lift_cap = float(quality.lift.quantile(0.99))
    shown = quality[quality.lift <= lift_cap]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(shown.lift, shown.rule_presence_rate, s=12, alpha=0.45, c=shown.support_count, cmap="plasma")
    ax.set_xlabel("Original Lift (shown through 99th percentile)")
    ax.set_ylabel("Bootstrap presence rate")
    ax.set_title("Lift vs Bootstrap Stability")
    _save(fig, "lift_vs_stability.png"); created.append("lift_vs_stability.png")

    shown_flags = flags.sort_values("rule_count").tail(10)
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(shown_flags.flag, shown_flags.rule_count, color="#ef4444")
    ax.set_xlabel("Flagged rules (flags may overlap)")
    ax.set_title("Transparent Misleading-Rule Warning Counts")
    _save(fig, "misleading_rule_flag_counts.png"); created.append("misleading_rule_flag_counts.png")

    comparison = quality.assign(stability_group=np.where(quality.rule_presence_rate >= 0.8, "Very stable", np.where(quality.rule_presence_rate < 0.2, "Unstable", "Other")))
    groups = [comparison.loc[comparison.stability_group.eq(group), "support_count"] for group in ["Very stable", "Other", "Unstable"]]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.boxplot(groups, tick_labels=["Very stable", "Other", "Unstable"], showfliers=False)
    ax.set_ylabel("Original support count")
    ax.set_title("Stable vs Unstable Rule Support (outliers hidden for readability)")
    _save(fig, "stable_vs_unstable_rules.png"); created.append("stable_vs_unstable_rules.png")

    fig, ax = plt.subplots(figsize=(7, 5))
    values = [len(redundant), len(quality)-len(redundant)]
    ax.bar(["Subsumed", "Nonredundant"], values, color=["#f97316", "#16a34a"])
    ax.set_ylabel("Rules")
    ax.set_title("Phase 5 Logical Redundancy Analysis")
    ax.bar_label(ax.containers[0], fmt="%d", padding=3)
    _save(fig, "redundancy_analysis_summary.png"); created.append("redundancy_analysis_summary.png")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(tiers.evidence_tier, tiers.rule_count, color=["#15803d", "#65a30d", "#f59e0b", "#dc2626"])
    ax.set_ylabel("Rules")
    ax.set_title("Evidence-Tier Distribution")
    ax.bar_label(ax.containers[0], fmt="%d", padding=3)
    _save(fig, "evidence_tier_distribution.png"); created.append("evidence_tier_distribution.png")

    fig, ax = plt.subplots(figsize=(9, 6))
    for (protocol, algorithm), group in scalability.groupby(["protocol", "algorithm"]):
        ax.plot(group.subset_fraction*100, group.median_runtime_seconds, marker="o", label=f"{protocol[0]} / {algorithm}")
    ax.set_xlabel("Transaction subset (%)")
    ax.set_ylabel("Median runtime across seeds (seconds)")
    ax.set_title("Corrected Scalability: Fixed Proportion vs Fixed Count")
    ax.legend(ncol=2)
    ax.grid(alpha=0.25)
    _save(fig, "corrected_scalability_comparison.png"); created.append("corrected_scalability_comparison.png")

    subset = original_corrected[(original_corrected.protocol.eq("A_fixed_support_proportion")) & (original_corrected.algorithm.eq("FP-Growth"))]
    fig, ax = plt.subplots(figsize=(9, 6))
    for source, group in subset.groupby("source"):
        ax.plot(group.subset_fraction*100, group.itemset_count, marker="o", label=source)
    ax.set_xlabel("Transaction subset (%)")
    ax.set_ylabel("Itemset count")
    ax.set_title("Original Time Prefix vs Corrected Random-Subset Median")
    ax.legend()
    ax.grid(alpha=0.25)
    _save(fig, "original_vs_corrected_scalability.png"); created.append("original_vs_corrected_scalability.png")

    action_plot = actions.sort_values("rule_count")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(action_plot.action_category, action_plot.rule_count, color="#0ea5e9")
    ax.set_xlabel("Rules")
    ax.set_title("Business Action Candidate Categories (not commercially validated)")
    _save(fig, "business_action_category_distribution.png"); created.append("business_action_category_distribution.png")
    return created


if __name__ == "__main__":
    print(generate_advanced_figures())
