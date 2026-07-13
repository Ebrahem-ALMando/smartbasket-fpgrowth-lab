"""Readable FP-Tree implementation for a tiny, deterministic teaching example."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Sequence


@dataclass
class FPNode:
    """One FP-Tree node with parent, children, and same-item node link."""

    node_id: int
    item: str | None
    count: int
    parent: FPNode | None
    children: dict[str, FPNode] = field(default_factory=dict)
    node_link: FPNode | None = None

    def prefix_path(self) -> tuple[str, ...]:
        """Return the item path before this node, excluding the root and node."""
        path: list[str] = []
        current = self.parent
        while current is not None and current.item is not None:
            path.append(current.item)
            current = current.parent
        return tuple(reversed(path))


@dataclass
class HeaderEntry:
    """Global support and linked-list endpoints for one frequent item."""

    support_count: int
    head: FPNode | None = None
    tail: FPNode | None = None


@dataclass(frozen=True)
class InsertionEvent:
    """Created and incremented nodes produced by one transaction insertion."""

    created_node_ids: tuple[int, ...]
    incremented_node_ids: tuple[int, ...]


WeightedTransaction = tuple[tuple[str, ...], int]


def educational_transactions() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return the clearly labelled deterministic educational basket fixture."""
    return (
        ("T1", ("Bread", "Milk", "Butter")),
        ("T2", ("Bread", "Milk")),
        ("T3", ("Bread", "Butter")),
        ("T4", ("Milk", "Butter")),
        ("T5", ("Bread", "Milk", "Eggs")),
        ("T6", ("Bread", "Milk", "Butter", "Coffee")),
    )


def count_item_frequencies(
    transactions: Iterable[WeightedTransaction],
) -> dict[str, int]:
    """Count transaction-level item frequency with optional integer weights."""
    counts: Counter[str] = Counter()
    for items, weight in transactions:
        if weight <= 0:
            raise ValueError("Transaction weights must be positive integers")
        for item in set(items):
            counts[item] += weight
    return dict(sorted(counts.items()))


class FPTree:
    """Small educational FP-Tree with deterministic insertion and mining."""

    def __init__(self, item_supports: dict[str, int]) -> None:
        if not item_supports:
            raise ValueError("An FP-Tree requires at least one frequent item")
        self.item_supports = dict(item_supports)
        self.order = tuple(
            sorted(item_supports, key=lambda item: (-item_supports[item], item))
        )
        self._rank = {item: rank for rank, item in enumerate(self.order)}
        self._next_node_id = 1
        self.root = FPNode(node_id=0, item=None, count=0, parent=None)
        self.header_table = {
            item: HeaderEntry(support_count=item_supports[item]) for item in self.order
        }

    @classmethod
    def build(
        cls,
        weighted_transactions: Sequence[WeightedTransaction],
        minimum_support_count: int,
    ) -> FPTree | None:
        """Build a tree from weighted transactions after support filtering."""
        if minimum_support_count < 1:
            raise ValueError("minimum_support_count must be at least one")
        frequencies = count_item_frequencies(weighted_transactions)
        frequent = {
            item: count
            for item, count in frequencies.items()
            if count >= minimum_support_count
        }
        if not frequent:
            return None
        tree = cls(frequent)
        for items, weight in weighted_transactions:
            tree.insert(items, count=weight)
        return tree

    def ordered_items(self, transaction: Sequence[str]) -> tuple[str, ...]:
        """Filter and deterministically order a transaction for insertion."""
        included = {item for item in transaction if item in self._rank}
        return tuple(sorted(included, key=self._rank.__getitem__))

    def insert(self, transaction: Sequence[str], *, count: int = 1) -> InsertionEvent:
        """Insert one transaction, reusing shared prefixes and updating links."""
        if count < 1:
            raise ValueError("Insertion count must be positive")
        current = self.root
        created: list[int] = []
        incremented: list[int] = []
        for item in self.ordered_items(transaction):
            child = current.children.get(item)
            if child is None:
                child = FPNode(
                    node_id=self._next_node_id,
                    item=item,
                    count=count,
                    parent=current,
                )
                self._next_node_id += 1
                current.children[item] = child
                self._append_header_link(item, child)
                created.append(child.node_id)
            else:
                child.count += count
                incremented.append(child.node_id)
            current = child
        return InsertionEvent(tuple(created), tuple(incremented))

    def _append_header_link(self, item: str, node: FPNode) -> None:
        entry = self.header_table[item]
        if entry.head is None:
            entry.head = entry.tail = node
        else:
            assert entry.tail is not None
            entry.tail.node_link = node
            entry.tail = node

    def nodes(self) -> Iterator[FPNode]:
        """Yield every node in deterministic pre-order, including the root."""
        stack = [self.root]
        while stack:
            node = stack.pop()
            yield node
            ordered_children = sorted(
                node.children.values(), key=lambda child: (self._rank[child.item], child.node_id)
            )
            stack.extend(reversed(ordered_children))

    def linked_nodes(self, item: str) -> Iterator[FPNode]:
        """Follow the header-table node-link chain for an item."""
        current = self.header_table[item].head
        while current is not None:
            yield current
            current = current.node_link

    def conditional_pattern_base(
        self, item: str
    ) -> tuple[tuple[tuple[str, ...], int], ...]:
        """Return non-empty prefix paths and counts for the requested item."""
        if item not in self.header_table:
            raise KeyError(item)
        paths = [
            (node.prefix_path(), node.count)
            for node in self.linked_nodes(item)
            if node.prefix_path()
        ]
        return tuple(paths)

    def mine(self, minimum_support_count: int) -> dict[frozenset[str], int]:
        """Extract all frequent itemsets recursively from this tree."""
        results: dict[frozenset[str], int] = {}
        self._mine_into(frozenset(), minimum_support_count, results)
        return results

    def _mine_into(
        self,
        suffix: frozenset[str],
        minimum_support_count: int,
        results: dict[frozenset[str], int],
    ) -> None:
        mining_order = sorted(
            self.header_table,
            key=lambda item: (self.header_table[item].support_count, item),
        )
        for item in mining_order:
            support = self.header_table[item].support_count
            itemset = suffix | {item}
            results[itemset] = support
            base = self.conditional_pattern_base(item)
            conditional_tree = FPTree.build(base, minimum_support_count) if base else None
            if conditional_tree is not None:
                conditional_tree._mine_into(itemset, minimum_support_count, results)


def build_educational_tree(
    minimum_support_count: int = 3,
) -> tuple[FPTree, dict[str, int]]:
    """Build the teaching tree and return raw item frequencies."""
    baskets = educational_transactions()
    weighted = [(items, 1) for _, items in baskets]
    frequencies = count_item_frequencies(weighted)
    tree = FPTree.build(weighted, minimum_support_count)
    if tree is None:
        raise RuntimeError("The educational threshold removed every item")
    return tree, frequencies
