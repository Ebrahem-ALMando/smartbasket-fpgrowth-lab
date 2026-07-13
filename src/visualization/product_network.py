"""Evidence-qualified, readable directed product-association network construction."""

from __future__ import annotations

import json

import networkx as nx
import pandas as pd


def filter_network_rules(
    rules: pd.DataFrame,
    *,
    stability_categories: tuple[str, ...] = ("Very stable",),
    minimum_confidence: float = 0.70,
    minimum_lift: float = 1.20,
    evidence_tiers: tuple[str, ...] = ("Tier A", "Tier B"),
    maximum_edges: int = 60,
    maximum_nodes: int = 40,
) -> pd.DataFrame:
    """Select stable one-to-one rules and enforce explicit readability caps."""
    eligible = rules.loc[
        rules.stability_category.isin(stability_categories)
        & rules.confidence.ge(minimum_confidence)
        & rules.lift.ge(minimum_lift)
        & rules.evidence_tier.isin(evidence_tiers)
        & ~rules.is_logically_redundant
        & rules.antecedent_length.eq(1)
        & rules.consequent_length.eq(1)
    ].copy()
    tier_rank = eligible.evidence_tier.map({"Tier A": 0, "Tier B": 1}).fillna(9)
    eligible = eligible.assign(_tier_rank=tier_rank).sort_values(
        ["_tier_rank", "rule_presence_rate", "confidence", "lift", "support_count", "rule_key"],
        ascending=[True, False, False, False, False, True],
        kind="mergesort",
    )
    chosen = []
    nodes: set[str] = set()
    for index, row in eligible.iterrows():
        source = json.loads(row.antecedent_codes)[0]
        target = json.loads(row.consequent_codes)[0]
        if len(nodes | {source, target}) > maximum_nodes:
            continue
        chosen.append(index)
        nodes.update([source, target])
        if len(chosen) >= maximum_edges:
            break
    return eligible.loc[chosen].drop(columns="_tier_rank").reset_index(drop=True)


def build_product_network(
    rules: pd.DataFrame,
    *,
    maximum_edges: int = 60,
    maximum_nodes: int = 40,
) -> tuple[nx.DiGraph, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build graph and auditable node, edge, and summary tables."""
    selected = filter_network_rules(
        rules, maximum_edges=maximum_edges, maximum_nodes=maximum_nodes
    )
    graph = nx.DiGraph()
    edge_rows = []
    for row in selected.itertuples(index=False):
        source = json.loads(row.antecedent_codes)[0]
        target = json.loads(row.consequent_codes)[0]
        source_description = json.loads(row.antecedent_descriptions)[0].split(" — ", 1)[-1]
        target_description = json.loads(row.consequent_descriptions)[0].split(" — ", 1)[-1]
        graph.add_node(source, description=source_description, support=row.antecedent_support)
        graph.add_node(target, description=target_description, support=row.consequent_support)
        graph.add_edge(
            source,
            target,
            rule_key=row.rule_key,
            support=row.support,
            support_count=row.support_count,
            confidence=row.confidence,
            lift=row.lift,
            stability=row.rule_presence_rate,
            stability_category=row.stability_category,
            evidence_tier=row.evidence_tier,
        )
        edge_rows.append(
            {
                "source_code": source,
                "source_description": source_description,
                "target_code": target,
                "target_description": target_description,
                "rule_key": row.rule_key,
                "support": row.support,
                "support_count": row.support_count,
                "confidence": row.confidence,
                "lift": row.lift,
                "presence_rate": row.rule_presence_rate,
                "stability_category": row.stability_category,
                "evidence_tier": row.evidence_tier,
            }
        )
    components = list(nx.weakly_connected_components(graph))
    component_by_node = {
        node: component_id
        for component_id, component in enumerate(components, start=1)
        for node in component
    }
    node_rows = []
    for node, attributes in graph.nodes(data=True):
        node_rows.append(
            {
                "product_code": node,
                "product_description": attributes["description"],
                "transaction_support": attributes["support"],
                "in_degree": graph.in_degree(node),
                "out_degree": graph.out_degree(node),
                "total_degree": graph.degree(node),
                "weighted_in_degree_confidence": graph.in_degree(node, weight="confidence"),
                "weighted_out_degree_confidence": graph.out_degree(node, weight="confidence"),
                "component_id": component_by_node[node],
            }
        )
    nodes = pd.DataFrame(node_rows).sort_values(
        ["total_degree", "transaction_support", "product_code"],
        ascending=[False, False, True],
    )
    edges = pd.DataFrame(edge_rows)
    summary = pd.DataFrame(
        [
            {"metric": "node_count", "value": graph.number_of_nodes()},
            {"metric": "directed_edge_count", "value": graph.number_of_edges()},
            {"metric": "weakly_connected_components", "value": len(components)},
            {"metric": "largest_component_nodes", "value": max(map(len, components), default=0)},
            {"metric": "maximum_nodes_filter", "value": maximum_nodes},
            {"metric": "maximum_edges_filter", "value": maximum_edges},
            {"metric": "minimum_presence_rate", "value": 0.80},
            {"metric": "minimum_confidence", "value": 0.70},
            {"metric": "minimum_lift", "value": 1.20},
        ]
    )
    return graph, nodes.reset_index(drop=True), edges, summary
