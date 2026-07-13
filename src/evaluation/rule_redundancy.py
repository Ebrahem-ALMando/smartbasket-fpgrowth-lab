"""Reproducible subsumption analysis for longer association rules."""

from __future__ import annotations

import json
from itertools import combinations

import pandas as pd


def detect_redundant_rules(
    rules: pd.DataFrame,
    *,
    maximum_confidence_difference: float = 0.05,
    maximum_relative_lift_gain: float = 0.10,
) -> pd.DataFrame:
    """Flag longer antecedents adding little over a simpler rule."""
    records = rules.set_index("rule_key")
    parsed = {
        key: (
            frozenset(json.loads(row.antecedent_codes)),
            tuple(json.loads(row.consequent_codes)),
        )
        for key, row in records.iterrows()
    }
    lookup = {(consequent, antecedent): key for key, (antecedent, consequent) in parsed.items()}
    output: list[dict[str, object]] = []
    for key, (antecedent, consequent) in parsed.items():
        if len(antecedent) <= 1:
            continue
        current = records.loc[key]
        best: dict[str, object] | None = None
        ordered = sorted(antecedent)
        for length in range(len(ordered) - 1, 0, -1):
            for subset in combinations(ordered, length):
                simpler_key = lookup.get((consequent, frozenset(subset)))
                if simpler_key is None:
                    continue
                simpler = records.loc[simpler_key]
                confidence_difference = abs(float(current.confidence) - float(simpler.confidence))
                relative_lift_gain = (
                    (float(current.lift) - float(simpler.lift)) / float(simpler.lift)
                    if float(simpler.lift) != 0
                    else float("inf")
                )
                is_redundant = (
                    confidence_difference <= maximum_confidence_difference
                    and relative_lift_gain <= maximum_relative_lift_gain
                )
                candidate = {
                    "rule_key": key,
                    "simpler_rule_key": simpler_key,
                    "antecedent_length": len(antecedent),
                    "simpler_antecedent_length": len(subset),
                    "confidence": float(current.confidence),
                    "simpler_confidence": float(simpler.confidence),
                    "absolute_confidence_difference": confidence_difference,
                    "lift": float(current.lift),
                    "simpler_lift": float(simpler.lift),
                    "relative_lift_gain": relative_lift_gain,
                    "is_redundant": is_redundant,
                    "criterion": (
                        f"abs confidence difference <= {maximum_confidence_difference}; "
                        f"relative lift gain <= {maximum_relative_lift_gain}"
                    ),
                }
                if is_redundant and (
                    best is None
                    or confidence_difference < float(best["absolute_confidence_difference"])
                ):
                    best = candidate
        if best is not None:
            output.append(best)
    columns = [
        "rule_key",
        "simpler_rule_key",
        "antecedent_length",
        "simpler_antecedent_length",
        "confidence",
        "simpler_confidence",
        "absolute_confidence_difference",
        "lift",
        "simpler_lift",
        "relative_lift_gain",
        "is_redundant",
        "criterion",
    ]
    return pd.DataFrame(output, columns=columns).sort_values(
        ["absolute_confidence_difference", "relative_lift_gain", "rule_key"],
        kind="mergesort",
    ).reset_index(drop=True)
