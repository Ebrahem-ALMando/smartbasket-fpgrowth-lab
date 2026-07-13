"""Non-causal explanation text for rule-based basket suggestions."""

from __future__ import annotations


def recommendation_explanation(
    *,
    rule_key: str,
    confidence: float,
    lift: float,
    presence_rate: float,
    evidence_tier: str,
) -> str:
    """Return a concise explanation without causal or probability claims."""
    return (
        f"Rule {rule_key} matched the current basket. Confidence={confidence:.3f}, "
        f"Lift={lift:.3f}, Bootstrap presence={presence_rate:.2f}, {evidence_tier}. "
        "This is a non-personalized association, not a purchase prediction or causal claim."
    )
