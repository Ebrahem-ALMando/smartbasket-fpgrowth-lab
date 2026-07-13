"""Static and self-contained Plotly exports for the product network."""

from __future__ import annotations

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from src.data.export import save_csv
from src.data.paths import project_path
from src.visualization.product_network import build_product_network


def export_product_network() -> dict[str, int]:
    """Create auditable tables, static preview, and portable HTML network."""
    rules = pd.read_csv(
        project_path("outputs", "tables", "rule_quality_audit.csv")
    )
    graph, nodes, edges, summary = build_product_network(rules)
    save_csv(nodes, project_path("outputs", "tables", "product_network_nodes.csv"))
    save_csv(edges, project_path("outputs", "tables", "product_network_edges.csv"))
    save_csv(summary, project_path("outputs", "tables", "product_network_summary.csv"))
    positions = nx.spring_layout(graph, seed=5701, k=1.4)

    fig_static, ax = plt.subplots(figsize=(13, 10))
    sizes = [500 + 9000 * graph.nodes[node]["support"] for node in graph.nodes]
    widths = [1 + 4 * graph.edges[edge]["confidence"] for edge in graph.edges]
    nx.draw_networkx_edges(
        graph,
        positions,
        ax=ax,
        arrows=True,
        arrowsize=14,
        width=widths,
        alpha=0.45,
        edge_color="#64748b",
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        ax=ax,
        node_size=sizes,
        node_color="#38bdf8",
        edgecolors="#0f172a",
        linewidths=0.8,
    )
    nx.draw_networkx_labels(
        graph,
        positions,
        labels={node: node for node in graph.nodes},
        font_size=8,
        ax=ax,
    )
    ax.set_title(
        "Stable Evidence-Qualified Product Association Network\n"
        "Node size = support; edge width = confidence; directed and non-causal"
    )
    ax.axis("off")
    fig_static.tight_layout()
    preview_path = project_path("outputs", "figures", "product_network_preview.png")
    fig_static.savefig(preview_path, dpi=300, bbox_inches="tight")
    plt.close(fig_static)

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    mid_x, mid_y, mid_hover = [], [], []
    annotations = []
    for source, target, attrs in graph.edges(data=True):
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        mid_x.append((x0 + x1) / 2)
        mid_y.append((y0 + y1) / 2)
        mid_hover.append(
            f"{attrs['rule_key']}<br>Support={attrs['support']:.4f} "
            f"(n={attrs['support_count']})<br>Confidence={attrs['confidence']:.3f} "
            f"Lift={attrs['lift']:.3f}<br>Presence={attrs['stability']:.2f} "
            f"{attrs['stability_category']}<br>{attrs['evidence_tier']}"
        )
        annotations.append(
            dict(
                ax=x1,
                ay=y1,
                x=x0,
                y=y0,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=0.8,
                arrowwidth=max(0.8, 2.5 * attrs["confidence"]),
                arrowcolor="rgba(71,85,105,0.45)",
                standoff=10,
            )
        )
    node_x, node_y, hover, node_size = [], [], [], []
    for node in graph.nodes:
        x, y = positions[node]
        attrs = graph.nodes[node]
        node_x.append(x)
        node_y.append(y)
        node_size.append(12 + 150 * attrs["support"])
        hover.append(
            f"{node} — {attrs['description']}<br>Support={attrs['support']:.4f}<br>"
            f"In={graph.in_degree(node)}, Out={graph.out_degree(node)}"
        )
    figure = go.Figure(
        data=[
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                line=dict(width=1, color="rgba(100,116,139,0.35)"),
                hoverinfo="skip",
            ),
            go.Scatter(
                x=mid_x,
                y=mid_y,
                mode="markers",
                marker=dict(size=12, opacity=0.05),
                text=mid_hover,
                hovertemplate="%{text}<extra></extra>",
            ),
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers+text",
                text=list(graph.nodes),
                textposition="top center",
                marker=dict(size=node_size, color="#38bdf8", line=dict(width=1, color="#0f172a")),
                hovertext=hover,
                hovertemplate="%{hovertext}<extra></extra>",
            ),
        ]
    )
    figure.update_layout(
        title="Stable Product Association Network — descriptive, not causal",
        showlegend=False,
        annotations=annotations,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        template="plotly_white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    html_path = project_path(
        "outputs", "interactive", "product_association_network.html"
    )
    figure.write_html(html_path, include_plotlyjs=True, full_html=True)
    return {"network_nodes": len(nodes), "network_edges": len(edges), "components": int(summary.loc[summary.metric.eq('weakly_connected_components'), 'value'].iloc[0])}


if __name__ == "__main__":
    print(export_product_network())
