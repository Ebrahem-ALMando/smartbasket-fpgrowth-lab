"""Cautious, traceable business-action candidates from evidence-qualified rules."""

from __future__ import annotations

import pandas as pd

from src.data.export import save_csv
from src.data.paths import project_path


def _action_category(row: pd.Series) -> str:
    total_length = int(row.antecedent_length + row.consequent_length)
    if row.evidence_tier == "Tier A":
        if total_length >= 3:
            return "Product bundle candidate"
        if row.support_count >= 180:
            return "Co-display candidate"
        return "Cross-sell candidate"
    if row.evidence_tier == "Tier B":
        return "Promotional test candidate"
    if row.evidence_tier == "Tier C":
        return "Monitor for more evidence"
    return "Reject from commercial interpretation"


def generate_business_actions() -> dict[str, int]:
    """Create one non-causal, externally testable action record per rule."""
    rules = pd.read_csv(project_path("outputs", "tables", "rule_quality_audit.csv"))
    actions = rules.copy()
    actions["action_category"] = actions.apply(_action_category, axis=1)
    actions["action_reason"] = actions.apply(
        lambda row: (
            f"{row.evidence_tier}; {row.stability_category}; presence={row.rule_presence_rate:.2f}; "
            f"support count={row.support_count}; confidence={row.confidence:.3f}; lift={row.lift:.3f}."
        ),
        axis=1,
    )
    actions["limitation"] = (
        "Observed association only; no causal, revenue, purchase-probability, or intervention effect was measured."
    )
    actions["suggested_validation_step"] = actions.action_category.map(
        {
            "Product bundle candidate": "Review product compatibility, then run a controlled bundle test.",
            "Cross-sell candidate": "Test a limited non-personalized cross-sell treatment against a control.",
            "Co-display candidate": "Use a controlled merchandising experiment before any rollout.",
            "Promotional test candidate": "Collect more observations and test a small promotion with a control.",
            "Monitor for more evidence": "Monitor new transactions and repeat stability analysis.",
            "Reject from commercial interpretation": "Do not operationalize; retain only for audit.",
        }
    )
    columns = [
        "rule_key",
        "action_category",
        "antecedent_codes",
        "antecedent_descriptions",
        "consequent_codes",
        "consequent_descriptions",
        "support",
        "support_count",
        "confidence",
        "lift",
        "rule_presence_rate",
        "stability_category",
        "evidence_tier",
        "quality_flags",
        "action_reason",
        "limitation",
        "suggested_validation_step",
    ]
    actions = actions[columns].sort_values(
        ["action_category", "evidence_tier", "rule_presence_rate", "support_count", "rule_key"],
        ascending=[True, True, False, False, True],
        kind="mergesort",
    )
    summary = (
        actions.groupby("action_category", as_index=False)
        .agg(rule_count=("rule_key", "size"))
        .assign(rule_percentage=lambda frame: 100 * frame.rule_count / len(actions))
        .sort_values("rule_count", ascending=False)
    )
    more_evidence = actions.loc[
        actions.action_category.isin(
            ["Monitor for more evidence", "Reject from commercial interpretation"]
        )
    ]
    save_csv(actions, project_path("outputs", "tables", "business_action_candidates.csv"))
    save_csv(summary, project_path("outputs", "tables", "business_action_summary.csv"))
    save_csv(
        more_evidence,
        project_path("outputs", "tables", "rules_requiring_more_evidence.csv"),
    )
    counts = actions.action_category.value_counts()
    return {category: int(count) for category, count in counts.items()}


if __name__ == "__main__":
    print(generate_business_actions())
