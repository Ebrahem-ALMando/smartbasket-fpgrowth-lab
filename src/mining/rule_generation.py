"""Association-rule generation, canonicalization, filtering, and interpretation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from itertools import combinations

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import association_rules

from src.mining.itemset_utils import (
    canonical_itemset,
    describe_items,
    itemset_key,
    serialize_items,
)


RULE_METRICS = (
    "antecedent support",
    "consequent support",
    "support",
    "confidence",
    "lift",
    "leverage",
    "conviction",
)


def canonical_rule_key(antecedent: object, consequent: object) -> str:
    """Return a stable directional key for two item iterables."""
    return f"{itemset_key(antecedent)} => {itemset_key(consequent)}"  # type: ignore[arg-type]


def _descriptive_interpretation(
    antecedent_labels: tuple[str, ...],
    consequent_labels: tuple[str, ...],
    confidence: float,
    lift: float,
) -> str:
    left = "; ".join(antecedent_labels)
    right = "; ".join(consequent_labels)
    return (
        f"Among transactions containing [{left}], [{right}] also appears with "
        f"Confidence {confidence:.3f}; Lift {lift:.3f} compares this co-occurrence "
        "with the consequent's baseline frequency and does not imply causation."
    )


def generate_rules(
    frequent_itemsets: pd.DataFrame,
    *,
    transaction_count: int,
    descriptions: Mapping[str, str],
    minimum_confidence: float = 0.0,
) -> pd.DataFrame:
    """Generate all qualifying rules and return a stable export-ready schema."""
    if frequent_itemsets.empty or not frequent_itemsets["itemsets"].map(len).gt(1).any():
        return pd.DataFrame()
    raw = association_rules(
        frequent_itemsets[["support", "itemsets"]],
        num_itemsets=transaction_count,
        metric="confidence",
        min_threshold=minimum_confidence,
        return_metrics=list(RULE_METRICS),
    )
    rows: list[dict[str, object]] = []
    for rule in raw.itertuples(index=False, name=None):
        values = dict(zip(raw.columns, rule))
        antecedent = canonical_itemset(values["antecedents"])
        consequent = canonical_itemset(values["consequents"])
        antecedent_labels = describe_items(antecedent, descriptions)
        consequent_labels = describe_items(consequent, descriptions)
        support = float(values["support"])
        conviction = float(values["conviction"])
        confidence = float(values["confidence"])
        lift = float(values["lift"])
        rows.append(
            {
                "rule_key": canonical_rule_key(antecedent, consequent),
                "antecedent_codes": serialize_items(antecedent),
                "antecedent_descriptions": json.dumps(
                    antecedent_labels, ensure_ascii=False
                ),
                "consequent_codes": serialize_items(consequent),
                "consequent_descriptions": json.dumps(
                    consequent_labels, ensure_ascii=False
                ),
                "antecedent_length": len(antecedent),
                "consequent_length": len(consequent),
                "antecedent_support": float(values["antecedent support"]),
                "consequent_support": float(values["consequent support"]),
                "support": support,
                "support_count": int(round(support * transaction_count)),
                "confidence": confidence,
                "lift": lift,
                "leverage": float(values["leverage"]),
                "conviction": conviction,
                "conviction_is_infinite": bool(np.isposinf(conviction)),
                "interpretation": _descriptive_interpretation(
                    antecedent_labels, consequent_labels, confidence, lift
                ),
            }
        )
    rules = pd.DataFrame(rows).drop_duplicates("rule_key")
    numeric = [
        "antecedent_support",
        "consequent_support",
        "support",
        "confidence",
        "lift",
        "leverage",
    ]
    rules["key_metrics_finite"] = np.isfinite(rules[numeric]).all(axis=1)
    rules["conviction_valid"] = rules["conviction"].notna() & (
        np.isfinite(rules["conviction"]) | np.isposinf(rules["conviction"])
    )
    return rules.sort_values(
        ["support", "confidence", "lift", "rule_key"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def mark_basic_redundancy(rules: pd.DataFrame, *, tolerance: float = 1e-12) -> pd.Series:
    """Mark rules dominated by a subset antecedent for the same consequent."""
    if rules.empty:
        return pd.Series(dtype=bool, index=rules.index)
    antecedents = rules["antecedent_codes"].map(lambda value: frozenset(json.loads(value)))
    consequents = rules["consequent_codes"].map(lambda value: tuple(json.loads(value)))
    redundant = pd.Series(False, index=rules.index)
    lookup = {
        (consequents.loc[index], antecedents.loc[index]): (
            float(rules.loc[index, "confidence"]),
            float(rules.loc[index, "lift"]),
        )
        for index in rules.index
    }
    for index in rules.index:
        current_antecedent = antecedents.loc[index]
        if len(current_antecedent) <= 1:
            continue
        ordered = sorted(current_antecedent)
        for subset_length in range(1, len(ordered)):
            for subset_items in combinations(ordered, subset_length):
                candidate = lookup.get(
                    (consequents.loc[index], frozenset(subset_items))
                )
                if candidate is not None and (
                    candidate[0] + tolerance >= rules.loc[index, "confidence"]
                    and candidate[1] + tolerance >= rules.loc[index, "lift"]
                ):
                    redundant.loc[index] = True
                    break
            if redundant.loc[index]:
                break
    return redundant


def select_rules(
    rules: pd.DataFrame,
    *,
    minimum_support: float,
    minimum_support_count: int,
    minimum_confidence: float,
    minimum_lift: float,
) -> pd.DataFrame:
    """Apply documented multi-metric filters and basic redundancy control."""
    if rules.empty:
        return rules.copy()
    candidates = rules.loc[
        (rules["support"] + 1e-15 >= minimum_support)
        & (rules["support_count"] >= minimum_support_count)
        & (rules["confidence"] >= minimum_confidence)
        & (rules["lift"] >= minimum_lift)
        & rules["key_metrics_finite"]
        & rules["conviction_valid"]
    ].copy()
    candidates["is_redundant"] = mark_basic_redundancy(candidates)
    return candidates.loc[~candidates["is_redundant"]].sort_values(
        ["lift", "confidence", "support", "rule_key"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
