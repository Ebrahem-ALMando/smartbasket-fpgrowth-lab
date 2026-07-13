"""Focused Phase 4 tests using only tiny labelled fixtures and Phase 3 metadata."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation.itemset_equivalence import compare_itemsets
from src.evaluation.mining_benchmark import measure_call
from src.mining.apriori_runner import run_apriori
from src.mining.basket_loader import load_prepared_basket
from src.mining.fp_tree_educational import build_educational_tree
from src.mining.fpgrowth_runner import run_fpgrowth
from src.mining.itemset_utils import canonical_itemset, itemset_key, serialize_items
from src.mining.rule_generation import canonical_rule_key, generate_rules
from src.mining.threshold_selection import (
    select_final_confidence,
    select_final_support,
    support_count,
)


def _tiny_basket() -> pd.DataFrame:
    """Clearly labelled validation fixture; not a project mining result."""
    return pd.DataFrame(
        [[1, 1, 0], [1, 1, 1], [1, 0, 1], [0, 1, 1]],
        columns=["A", "B", "C"],
        dtype=bool,
    )


def test_educational_tree_node_counts_and_shared_prefix() -> None:
    tree, _ = build_educational_tree()
    bread = tree.root.children["Bread"]
    assert bread.count == 5
    assert bread.children["Milk"].count == 4
    assert bread.children["Milk"].children["Butter"].count == 2
    assert len(tree.root.children) == 2


def test_header_table_node_links() -> None:
    tree, _ = build_educational_tree()
    assert [node.count for node in tree.linked_nodes("Butter")] == [2, 1, 1]
    assert tree.header_table["Butter"].support_count == 4


def test_conditional_pattern_bases() -> None:
    tree, _ = build_educational_tree()
    assert tree.conditional_pattern_base("Butter") == (
        (("Bread", "Milk"), 2),
        (("Bread",), 1),
        (("Milk",), 1),
    )
    assert tree.conditional_pattern_base("Milk") == ((("Bread",), 4),)


def test_manual_frequent_itemset_correctness() -> None:
    tree, _ = build_educational_tree()
    actual = {tuple(sorted(itemset)): count for itemset, count in tree.mine(3).items()}
    assert actual == {
        ("Bread",): 5,
        ("Butter",): 4,
        ("Milk",): 5,
        ("Bread", "Butter"): 3,
        ("Bread", "Milk"): 4,
        ("Butter", "Milk"): 3,
    }


def test_sparse_basket_loading_and_binary_validation() -> None:
    prepared = load_prepared_basket()
    assert prepared.matrix.shape == (17_901, 3_791)
    assert prepared.matrix.nnz == 473_636
    assert np.all(prepared.matrix.data == 1)
    assert str(prepared.to_sparse_boolean_frame().dtypes.iloc[0]).startswith("Sparse[bool")


def test_canonical_itemset_serialization() -> None:
    assert canonical_itemset(["B", "A", "B"]) == ("A", "B")
    assert itemset_key(["B", "A"]) == "A | B"
    assert serialize_items(["B", "A"]) == '["A", "B"]'


def test_support_count_calculation() -> None:
    assert support_count(0.005, 17_901) == 90
    assert support_count(0.01, 17_901) == 180


def test_rule_canonicalization() -> None:
    assert canonical_rule_key(["B", "A"], ["D", "C"]) == "A | B => C | D"


def test_rule_metric_sanity_on_hand_verifiable_fixture() -> None:
    run = run_fpgrowth(_tiny_basket(), minimum_support=0.5, maximum_length=3)
    rules = generate_rules(
        run.itemsets,
        transaction_count=4,
        descriptions={"A": "Alpha", "B": "Beta", "C": "Gamma"},
    )
    rule = rules.loc[rules.rule_key.eq("A => B")].iloc[0]
    assert rule.support == 0.5
    assert np.isclose(rule.confidence, 2 / 3)
    assert np.isclose(rule.lift, 8 / 9)
    assert np.isclose(rule.leverage, -0.0625)
    assert np.isclose(rule.conviction, 0.75)


def test_threshold_selection_is_deterministic() -> None:
    sweep = pd.DataFrame(
        [
            {
                "minimum_support": 0.02,
                "execution_status": "success",
                "length_2_count": 5,
                "length_3_count": 1,
                "frequent_itemset_count": 20,
                "rule_count_confidence_0_50": 30,
                "rule_count_confidence_0_70": 25,
                "rule_count_confidence_0_30": 40,
                "runtime_seconds": 1.0,
                "approximate_rss_delta_bytes": 100,
            },
            {
                "minimum_support": 0.01,
                "execution_status": "success",
                "length_2_count": 10,
                "length_3_count": 3,
                "frequent_itemset_count": 50,
                "rule_count_confidence_0_50": 60,
                "rule_count_confidence_0_70": 26,
                "rule_count_confidence_0_30": 100,
                "runtime_seconds": 2.0,
                "approximate_rss_delta_bytes": 200,
            },
        ]
    )
    selected = select_final_support(sweep)
    assert selected.minimum_support == 0.01
    assert select_final_confidence(selected) == 0.70


def test_fpgrowth_and_apriori_equivalence_on_tiny_fixture() -> None:
    basket = _tiny_basket()
    fp = run_fpgrowth(basket, minimum_support=0.5, maximum_length=3)
    ap = run_apriori(basket, minimum_support=0.5, maximum_length=3)
    _, summary = compare_itemsets(fp.itemsets, ap.itemsets)
    assert summary.equivalent
    assert summary.common_itemsets == 6


def test_itemset_comparison_tolerance() -> None:
    basket = _tiny_basket()
    fp = run_fpgrowth(basket, minimum_support=0.5, maximum_length=3).itemsets
    almost = fp.copy()
    almost.loc[0, "support"] += 5e-13
    _, accepted = compare_itemsets(fp, almost, absolute_tolerance=1e-12)
    _, rejected = compare_itemsets(fp, almost, absolute_tolerance=1e-14)
    assert accepted.equivalent
    assert not rejected.equivalent


def test_benchmark_metadata_completeness() -> None:
    measured = measure_call("fixture", lambda: [1, 2, 3])
    record = measured.benchmark.as_dict()
    assert measured.value == [1, 2, 3]
    assert record["status"] == "success"
    assert record["result_count"] == 3
    assert record["runtime_seconds"] >= 0
    assert {"rss_before_bytes", "rss_after_bytes", "memory_measurement"} <= record.keys()
