"""Generate auditable tables and step visualizations for the teaching FP-Tree."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.data.export import save_csv
from src.data.paths import ensure_directory, project_path
from src.mining.fp_tree_educational import (
    FPTree,
    build_educational_tree,
    count_item_frequencies,
    educational_transactions,
)


@dataclass(frozen=True)
class TreeSnapshot:
    """Serializable state after inserting one educational transaction."""

    transaction_id: str
    original_items: tuple[str, ...]
    ordered_items: tuple[str, ...]
    created_node_ids: tuple[int, ...]
    incremented_node_ids: tuple[int, ...]
    nodes: tuple[dict[str, object], ...]
    header_links: tuple[dict[str, object], ...]


def _snapshot(
    tree: FPTree,
    transaction_id: str,
    items: tuple[str, ...],
    created: tuple[int, ...],
    incremented: tuple[int, ...],
) -> TreeSnapshot:
    nodes = tuple(
        {
            "node_id": node.node_id,
            "item": node.item or "ROOT",
            "count": node.count,
            "parent_id": None if node.parent is None else node.parent.node_id,
        }
        for node in tree.nodes()
    )
    links = tuple(
        {
            "item": item,
            "support_count": entry.support_count,
            "node_ids": tuple(node.node_id for node in tree.linked_nodes(item)),
        }
        for item, entry in tree.header_table.items()
    )
    return TreeSnapshot(
        transaction_id=transaction_id,
        original_items=items,
        ordered_items=tree.ordered_items(items),
        created_node_ids=created,
        incremented_node_ids=incremented,
        nodes=nodes,
        header_links=links,
    )


def build_step_snapshots(minimum_support_count: int = 3) -> tuple[TreeSnapshot, ...]:
    """Insert the educational transactions one at a time and capture states."""
    baskets = educational_transactions()
    weighted = [(items, 1) for _, items in baskets]
    frequencies = count_item_frequencies(weighted)
    frequent = {
        item: count for item, count in frequencies.items() if count >= minimum_support_count
    }
    tree = FPTree(frequent)
    snapshots: list[TreeSnapshot] = []
    for transaction_id, items in baskets:
        event = tree.insert(items)
        snapshots.append(
            _snapshot(
                tree,
                transaction_id,
                items,
                event.created_node_ids,
                event.incremented_node_ids,
            )
        )
    return tuple(snapshots)


def _tree_positions(nodes: tuple[dict[str, object], ...]) -> dict[int, tuple[float, float]]:
    children: dict[int, list[int]] = {}
    depth = {0: 0}
    for node in nodes:
        node_id = int(node["node_id"])
        parent_id = node["parent_id"]
        if parent_id is not None:
            parent = int(parent_id)
            children.setdefault(parent, []).append(node_id)
            depth[node_id] = depth[parent] + 1
    for child_ids in children.values():
        child_ids.sort()
    positions: dict[int, tuple[float, float]] = {}
    next_leaf = 0.0

    def visit(node_id: int) -> float:
        nonlocal next_leaf
        node_children = children.get(node_id, [])
        if not node_children:
            x = next_leaf
            next_leaf += 1.0
        else:
            xs = [visit(child) for child in node_children]
            x = sum(xs) / len(xs)
        positions[node_id] = (x, -float(depth[node_id]))
        return x

    visit(0)
    return positions


def render_step_figure(snapshot: TreeSnapshot, output_path: Path) -> None:
    """Render one readable construction state with node and header evidence."""
    positions = _tree_positions(snapshot.nodes)
    node_by_id = {int(node["node_id"]): node for node in snapshot.nodes}
    fig, (tree_ax, header_ax) = plt.subplots(
        1, 2, figsize=(12, 6), gridspec_kw={"width_ratios": [3.2, 1.5]}
    )
    for node in snapshot.nodes:
        node_id = int(node["node_id"])
        parent_id = node["parent_id"]
        if parent_id is not None:
            x1, y1 = positions[int(parent_id)]
            x2, y2 = positions[node_id]
            tree_ax.plot([x1, x2], [y1, y2], color="#64748b", linewidth=1.5, zorder=1)
    for node_id, (x, y) in positions.items():
        node = node_by_id[node_id]
        if node_id in snapshot.created_node_ids:
            color = "#86efac"
        elif node_id in snapshot.incremented_node_ids:
            color = "#fde68a"
        else:
            color = "#dbeafe" if node_id else "#e2e8f0"
        tree_ax.scatter(x, y, s=1500, color=color, edgecolor="#1e293b", zorder=2)
        tree_ax.text(
            x,
            y,
            f"{node['item']}\ncount={node['count']}",
            ha="center",
            va="center",
            fontsize=9,
            zorder=3,
        )
    tree_ax.set_title(
        f"Insert {snapshot.transaction_id}: {', '.join(snapshot.original_items)}\n"
        f"Ordered: {', '.join(snapshot.ordered_items) or '(empty)'}"
    )
    tree_ax.axis("off")
    header_ax.axis("off")
    header_ax.set_title("Header Table and Node-Link chains", loc="left")
    header_lines = [
        f"{entry['item']} ({entry['support_count']}): "
        + " → ".join(f"node {node_id}" for node_id in entry["node_ids"])
        for entry in snapshot.header_links
    ]
    change_lines = [
        "",
        "Green = newly created",
        "Yellow = count incremented",
        f"Created: {list(snapshot.created_node_ids) or 'none'}",
        f"Incremented: {list(snapshot.incremented_node_ids) or 'none'}",
    ]
    header_ax.text(
        0,
        0.95,
        "\n".join(header_lines + change_lines),
        va="top",
        fontsize=10,
        linespacing=1.5,
    )
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _write_interactive_viewer(step_paths: list[Path], output_path: Path) -> None:
    images = [base64.b64encode(path.read_bytes()).decode("ascii") for path in step_paths]
    options = "".join(
        f'<option value="{index}">Step {index + 1}</option>'
        for index in range(len(images))
    )
    image_literals = ",\n".join(f'"data:image/png;base64,{image}"' for image in images)
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Manual FP-Tree Steps</title>
<style>body{{font-family:system-ui;margin:2rem;background:#f8fafc;color:#0f172a}}
.card{{max-width:1200px;margin:auto;background:white;padding:1rem;border-radius:12px;box-shadow:0 4px 20px #0001}}
img{{width:100%;height:auto}} select{{font-size:1rem;padding:.4rem}}</style></head>
<body><main class="card"><h1>Educational FP-Tree Construction</h1>
<p>This viewer uses the labelled six-transaction teaching example, not the UCI mining result.</p>
<label for="step">Construction state: </label><select id="step">{options}</select>
<img id="figure" alt="FP-Tree construction step"></main>
<script>const images=[{image_literals}]; const select=document.getElementById('step');
const figure=document.getElementById('figure'); function show(){{figure.src=images[Number(select.value)];}}
select.addEventListener('change',show); show();</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def generate_educational_outputs(minimum_support_count: int = 3) -> dict[str, object]:
    """Create all machine-readable and visual outputs for the manual example."""
    baskets = educational_transactions()
    tree, raw_frequencies = build_educational_tree(minimum_support_count)
    frequent_itemsets = tree.mine(minimum_support_count)
    table_dir = ensure_directory("outputs", "tables")

    save_csv(
        pd.DataFrame(
            [
                {"transaction_id": transaction_id, "items": " | ".join(items)}
                for transaction_id, items in baskets
            ]
        ),
        table_dir / "manual_fp_tree_transactions.csv",
    )
    save_csv(
        pd.DataFrame(
            [
                {
                    "item": item,
                    "support_count": count,
                    "is_frequent": count >= minimum_support_count,
                    "global_order": (
                        tree.order.index(item) + 1 if item in tree.order else pd.NA
                    ),
                }
                for item, count in sorted(raw_frequencies.items(), key=lambda pair: (-pair[1], pair[0]))
            ]
        ),
        table_dir / "manual_fp_tree_item_frequencies.csv",
    )
    save_csv(
        pd.DataFrame(
            [
                {
                    "item": item,
                    "support_count": entry.support_count,
                    "node_link_chain": " -> ".join(
                        str(node.node_id) for node in tree.linked_nodes(item)
                    ),
                    "node_counts": " -> ".join(
                        str(node.count) for node in tree.linked_nodes(item)
                    ),
                }
                for item, entry in tree.header_table.items()
            ]
        ),
        table_dir / "manual_fp_tree_header_table.csv",
    )
    save_csv(
        pd.DataFrame(
            [
                {
                    "itemset_key": " | ".join(sorted(itemset)),
                    "itemset_length": len(itemset),
                    "support_count": support,
                    "support": support / len(baskets),
                }
                for itemset, support in sorted(
                    frequent_itemsets.items(), key=lambda pair: (len(pair[0]), sorted(pair[0]))
                )
            ]
        ),
        table_dir / "manual_fp_tree_frequent_itemsets.csv",
    )
    conditional_rows = []
    for item in reversed(tree.order):
        base = tree.conditional_pattern_base(item)
        if not base:
            conditional_rows.append(
                {"target_item": item, "prefix_path": "", "path_count": 0}
            )
        else:
            conditional_rows.extend(
                {
                    "target_item": item,
                    "prefix_path": " | ".join(path),
                    "path_count": count,
                }
                for path, count in base
            )
    save_csv(
        pd.DataFrame(conditional_rows),
        table_dir / "manual_fp_tree_conditional_bases.csv",
    )

    snapshots = build_step_snapshots(minimum_support_count)
    figure_dir = ensure_directory("outputs", "figures", "manual_fp_tree_steps")
    step_paths: list[Path] = []
    for index, snapshot in enumerate(snapshots, start=1):
        path = figure_dir / f"step_{index:02d}_{snapshot.transaction_id.lower()}.png"
        render_step_figure(snapshot, path)
        step_paths.append(path)
    interactive_path = project_path("outputs", "interactive", "manual_fp_tree_steps.html")
    _write_interactive_viewer(step_paths, interactive_path)
    return {
        "minimum_support_count": minimum_support_count,
        "transaction_count": len(baskets),
        "frequent_itemset_count": len(frequent_itemsets),
        "step_figure_count": len(step_paths),
        "interactive_path": str(interactive_path.relative_to(project_path())),
    }


if __name__ == "__main__":
    print(generate_educational_outputs())
