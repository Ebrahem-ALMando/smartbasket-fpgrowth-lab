"""Metric formulas and explicit Python–WEKA numeric tolerances."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MetricTolerance:
    absolute: float
    relative: float = 0.0


METRIC_TOLERANCES: dict[str, MetricTolerance] = {
    "support": MetricTolerance(absolute=1e-12),
    "confidence": MetricTolerance(absolute=1e-12),
    "lift": MetricTolerance(absolute=1e-12),
    "leverage": MetricTolerance(absolute=1e-12),
    "conviction": MetricTolerance(absolute=1e-10, relative=1e-10),
}


def values_match(left: float, right: float, tolerance: MetricTolerance) -> bool:
    """Compare finite, missing, and infinite metrics without hiding semantics."""
    if math.isnan(left) or math.isnan(right):
        return math.isnan(left) and math.isnan(right)
    if math.isinf(left) or math.isinf(right):
        return left == right
    return math.isclose(
        left, right, abs_tol=tolerance.absolute, rel_tol=tolerance.relative
    )


def support_from_count(count: int, transaction_count: int) -> float:
    """Derive support proportion explicitly from API counts."""
    if transaction_count <= 0:
        raise ValueError("transaction_count must be positive")
    if not 0 <= count <= transaction_count:
        raise ValueError("support count is outside the transaction range")
    return count / transaction_count

