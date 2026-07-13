"""Tiny labelled fixtures for Phase 5 stability, quality, and interactive logic."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import sparse

from src.evaluation.bootstrap_stability import (
    BootstrapConfig,
    bootstrap_indices,
    run_bootstrap_resample,
)
from src.evaluation.metric_uncertainty import metric_interval
from src.evaluation.misleading_rules import detect_misleading_flags
from src.evaluation.rule_quality import _assign_evidence_tier
from src.evaluation.rule_redundancy import detect_redundant_rules
from src.evaluation.rule_stability import aggregate_rule_stability, stability_category
from src.evaluation.scalability_corrected import protocol_support
from src.mining.basket_loader import PreparedBasket
from src.recommendation.basket_recommender import BasketRecommender
from src.recommendation.business_actions import _action_category
from src.visualization.product_network import build_product_network, filter_network_rules
from src.visualization.threshold_explorer import filter_explorer_rules


def _quality_rules() -> pd.DataFrame:
    rows = []
    specifications = [
        ("A => B", ["A"], ["B"], 0.80, 3.0, 160, "Tier A"),
        ("B => A", ["B"], ["A"], 0.75, 2.5, 145, "Tier B"),
        ("A => C", ["A"], ["C"], 0.80, 2.0, 150, "Tier A"),
        ("A | B => C", ["A", "B"], ["C"], 0.82, 2.1, 120, "Tier C"),
    ]
    for key, antecedent, consequent, confidence, lift, count, tier in specifications:
        rows.append(
            {
                "rule_key": key,
                "antecedent_codes": json.dumps(antecedent),
                "antecedent_descriptions": json.dumps([f"{x} — Product {x}" for x in antecedent]),
                "consequent_codes": json.dumps(consequent),
                "consequent_descriptions": json.dumps([f"{x} — Product {x}" for x in consequent]),
                "antecedent_length": len(antecedent),
                "consequent_length": len(consequent),
                "antecedent_support": 0.10,
                "consequent_support": 0.09 if consequent == ["B"] else 0.06,
                "support": count / 1000,
                "support_count": count,
                "confidence": confidence,
                "lift": lift,
                "leverage": 0.01,
                "conviction": 2.0,
                "rule_presence_rate": 0.9 if tier in ["Tier A", "Tier B"] else 0.4,
                "stability_category": "Very stable" if tier in ["Tier A", "Tier B"] else "Weakly stable",
                "support_mean": count / 1000,
                "support_p025": count / 1100,
                "support_p975": count / 900,
                "confidence_mean": confidence,
                "confidence_p025": confidence - 0.05,
                "confidence_p975": confidence + 0.05,
                "lift_mean": lift,
                "lift_p025": lift - 0.4,
                "lift_p975": lift + 0.4,
                "is_logically_redundant": key == "A | B => C",
                "insufficient_business_evidence": False,
                "evidence_tier": tier,
            }
        )
    return pd.DataFrame(rows)


def test_bootstrap_reproducibility_and_sample_size() -> None:
    first = bootstrap_indices(50, 51001)
    second = bootstrap_indices(50, 51001)
    assert len(first) == 50
    assert np.array_equal(first, second)
    assert len(np.unique(first)) < 50


def test_canonical_rule_matching_and_presence_calculation() -> None:
    candidates = pd.DataFrame({"rule_key": ["A => B", "A => C"]})
    observations = pd.DataFrame(
        {
            "rule_key": ["A => B", "A => B", "A => C", "A => C"],
            "is_present": [True, True, True, False],
            "support": [0.1, 0.11, 0.08, 0.07],
            "confidence": [0.8, 0.82, 0.75, 0.65],
            "lift": [2.0, 2.1, 1.5, 1.4],
        }
    )
    stability, _ = aggregate_rule_stability(observations, candidates, successful_resamples=2)
    rates = stability.set_index("rule_key").rule_presence_rate
    assert rates["A => B"] == 1.0
    assert rates["A => C"] == 0.5
    assert stability_category(rates["A => C"]) == "Moderately stable"


def test_metric_interval_calculation() -> None:
    summary = metric_interval(pd.Series([1.0, 2.0, 3.0, np.nan]))
    assert summary["valid_observations"] == 3
    assert summary["mean"] == 2.0
    assert np.isclose(summary["std"], 1.0)
    assert summary["minimum"] == 1.0 and summary["maximum"] == 3.0


def test_failed_resample_is_recorded() -> None:
    matrix = sparse.csr_matrix(np.array([[1, 1], [1, 0], [0, 1], [1, 1]], dtype=np.uint8))
    prepared = PreparedBasket(
        matrix=matrix,
        product_codes=("A", "B"),
        descriptions={"A": "Alpha", "B": "Beta"},
        transaction_index=pd.DataFrame({"InvoiceNo": ["1", "2", "3", "4"]}),
    )
    observations, metadata = run_bootstrap_resample(
        prepared,
        pd.DataFrame({"rule_key": ["A => B"]}),
        seed=1,
        resample_id=1,
        config=BootstrapConfig(minimum_support=0.5, maximum_itemsets=0),
    )
    assert observations.empty
    assert metadata["status"] == "failed"
    assert "itemset safeguard exceeded" in metadata["failure_reason"]


def test_misleading_flags_and_consequent_baseline() -> None:
    rules = _quality_rules().copy()
    rules.loc[0, "lift"] = 1.3
    rules.loc[0, "support_count"] = 100
    flags = detect_misleading_flags(rules)
    first = flags.iloc[0]
    assert first.high_confidence_weak_lift
    assert first.common_consequent
    assert first.near_support_floor


def test_redundancy_detection() -> None:
    redundant = detect_redundant_rules(_quality_rules())
    row = redundant.loc[redundant.rule_key.eq("A | B => C")].iloc[0]
    assert row.is_redundant
    assert row.simpler_rule_key == "A => C"


def test_evidence_tier_assignment() -> None:
    row = pd.Series(
        {
            "stability_category": "Very stable",
            "insufficient_business_evidence": False,
            "is_logically_redundant": False,
            "support_count": 150,
            "wide_confidence_interval": False,
            "wide_lift_interval": False,
            "high_confidence_weak_lift": False,
        }
    )
    assert _assign_evidence_tier(row) == "Tier A"


def test_network_node_edge_generation_and_filtering() -> None:
    graph, nodes, edges, _ = build_product_network(_quality_rules(), maximum_edges=2, maximum_nodes=3)
    assert len(edges) <= 2 and len(nodes) <= 3
    assert graph.number_of_edges() == len(edges)
    filtered = filter_network_rules(_quality_rules(), evidence_tiers=("Tier A",), maximum_edges=10)
    assert filtered.evidence_tier.eq("Tier A").all()


def test_basket_antecedent_matching_and_current_item_exclusion() -> None:
    recommender = BasketRecommender(_quality_rules(), {"A": "Alpha", "B": "Beta", "C": "Gamma"})
    result = recommender.recommend(["A"])
    assert set(result.recommended_product_code) == {"B", "C"}
    assert "A" not in set(result.recommended_product_code)


def test_recommendation_tie_breaking_is_stable() -> None:
    recommender = BasketRecommender(_quality_rules(), {"A": "Alpha", "B": "Beta", "C": "Gamma"})
    first = recommender.recommend(["A"])
    second = recommender.recommend(["A"])
    pd.testing.assert_frame_equal(first, second)
    assert first.iloc[0].evidence_tier == "Tier A"


def test_empty_recommendation_behavior() -> None:
    recommender = BasketRecommender(_quality_rules(), {"A": "Alpha", "B": "Beta", "C": "Gamma"})
    assert recommender.recommend(["C"]).empty


def test_business_action_traceability() -> None:
    row = _quality_rules().iloc[0]
    assert _action_category(row) == "Cross-sell candidate"
    assert row.rule_key == "A => B"


def test_corrected_scalability_protocol_conversion() -> None:
    assert protocol_support("A_fixed_support_proportion", 4_475) == (0.005, 23)
    proportion, count = protocol_support("B_fixed_absolute_support_count", 4_475)
    assert np.isclose(proportion, 90 / 4_475)
    assert count == 90


def test_threshold_explorer_filtering_and_stable_order() -> None:
    rules = _quality_rules()
    first = filter_explorer_rules(rules, evidence_tier="Tier A", maximum_rules=10)
    second = filter_explorer_rules(rules, evidence_tier="Tier A", maximum_rules=10)
    assert first.evidence_tier.eq("Tier A").all()
    assert first.rule_key.tolist() == second.rule_key.tolist()
    assert first.rule_presence_rate.is_monotonic_decreasing
