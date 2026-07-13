"""Evidence-tier assignment and bilingual, non-causal rule dispositions."""

from __future__ import annotations

import pandas as pd

from src.data.export import save_csv
from src.data.paths import project_path
from src.evaluation.misleading_rules import (
    detect_misleading_flags,
    misleading_flag_summary,
)
from src.evaluation.rule_redundancy import detect_redundant_rules


def _assign_evidence_tier(row: pd.Series) -> str:
    if row.stability_category == "Unstable" or row.insufficient_business_evidence:
        return "Tier D"
    if row.is_logically_redundant or row.stability_category == "Weakly stable":
        return "Tier C"
    if (
        row.stability_category == "Very stable"
        and row.support_count >= 135
        and not row.wide_confidence_interval
        and not row.wide_lift_interval
        and not row.high_confidence_weak_lift
    ):
        return "Tier A"
    return "Tier B"


def _disposition(row: pd.Series) -> str:
    if row.is_logically_redundant:
        return "simplify"
    if row.evidence_tier == "Tier A":
        return "retain"
    if row.evidence_tier == "Tier B":
        return "monitor"
    if row.evidence_tier == "Tier D":
        return "reject from business interpretation"
    return "insufficient evidence"


def _arabic_explanation(row: pd.Series) -> str:
    return (
        f"القاعدة ضمن {row.evidence_tier} وباستقرار {row.stability_category} "
        f"(معدل حضور {row.rule_presence_rate:.2f})؛ الأعلام: {row.quality_flags}. "
        "هذا ارتباط وصفي لا يثبت السببية أو الأثر التجاري."
    )


def _english_explanation(row: pd.Series) -> str:
    return (
        f"{row.evidence_tier}; {row.stability_category} with presence rate "
        f"{row.rule_presence_rate:.2f}. Flags: {row.quality_flags}. "
        "The association is descriptive, non-causal, and requires external validation."
    )


def build_rule_quality_outputs() -> dict[str, int]:
    """Audit all Phase 4 candidates and save transparent Phase 5 outputs."""
    stability = pd.read_csv(
        project_path("outputs", "tables", "rule_stability_results.csv")
    )
    redundancy = detect_redundant_rules(stability)
    redundant_keys = set(redundancy["rule_key"])
    flags = detect_misleading_flags(stability)
    audit = stability.merge(flags, on="rule_key", how="left")
    audit["is_logically_redundant"] = audit["rule_key"].isin(redundant_keys)
    simpler = redundancy.set_index("rule_key")["simpler_rule_key"] if not redundancy.empty else pd.Series(dtype=str)
    audit["simpler_rule_key"] = audit["rule_key"].map(simpler).fillna("")
    audit["redundancy_status"] = audit["is_logically_redundant"].map(
        {True: "subsumed_by_simpler_rule", False: "nonredundant_under_phase5_criterion"}
    )
    audit["evidence_tier"] = audit.apply(_assign_evidence_tier, axis=1)
    audit["recommended_disposition"] = audit.apply(_disposition, axis=1)
    audit["arabic_quality_explanation"] = audit.apply(_arabic_explanation, axis=1)
    audit["english_technical_explanation"] = audit.apply(_english_explanation, axis=1)
    tier_order = pd.CategoricalDtype(["Tier A", "Tier B", "Tier C", "Tier D"], ordered=True)
    audit["_tier_order"] = audit["evidence_tier"].astype(tier_order)
    audit = audit.sort_values(
        ["_tier_order", "rule_presence_rate", "support_count", "confidence", "lift", "rule_key"],
        ascending=[True, False, False, False, False, True],
        kind="mergesort",
    ).drop(columns="_tier_order").reset_index(drop=True)

    stable_nonredundant = audit.loc[
        audit["rule_presence_rate"].ge(0.50) & ~audit["is_logically_redundant"]
    ].copy()
    final_candidates = audit.loc[
        audit["evidence_tier"].isin(["Tier A", "Tier B"])
        & ~audit["is_logically_redundant"]
        & ~audit["insufficient_business_evidence"]
    ].copy()
    tier_summary = (
        audit.groupby("evidence_tier", as_index=False)
        .agg(rule_count=("rule_key", "size"))
        .assign(rule_percentage=lambda frame: 100 * frame.rule_count / len(audit))
    )
    save_csv(audit, project_path("outputs", "tables", "rule_quality_audit.csv"))
    save_csv(
        misleading_flag_summary(flags),
        project_path("outputs", "tables", "misleading_rule_flags.csv"),
    )
    save_csv(redundancy, project_path("outputs", "tables", "redundant_rules.csv"))
    save_csv(
        stable_nonredundant,
        project_path("outputs", "tables", "nonredundant_stable_rules.csv"),
    )
    save_csv(tier_summary, project_path("outputs", "tables", "rule_evidence_tiers.csv"))
    save_csv(
        final_candidates,
        project_path("outputs", "tables", "final_interpretation_candidates.csv"),
    )
    return {
        "rules_evaluated": len(audit),
        "rules_with_any_flag": int(audit.flag_count.gt(0).sum()),
        "redundant_rules": len(redundancy),
        "nonredundant_stable_rules": len(stable_nonredundant),
        "final_interpretation_candidates": len(final_candidates),
        **{
            tier.lower().replace(" ", "_"): int(audit.evidence_tier.eq(tier).sum())
            for tier in ["Tier A", "Tier B", "Tier C", "Tier D"]
        },
    }


if __name__ == "__main__":
    print(build_rule_quality_outputs())
