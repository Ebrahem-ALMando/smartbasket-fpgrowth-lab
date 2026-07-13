"""Wall-clock and approximate process-memory measurement utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Callable, Generic, TypeVar

import psutil


T = TypeVar("T")


@dataclass(frozen=True)
class BenchmarkRecord:
    """Metadata for one algorithm invocation."""

    algorithm: str
    status: str
    runtime_seconds: float
    rss_before_bytes: int
    rss_after_bytes: int
    rss_delta_bytes: int
    result_count: int
    error_type: str
    error_message: str
    memory_measurement: str = "approximate process RSS before/after; not peak memory"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MeasuredResult(Generic[T]):
    """Successful result or failure plus its benchmark record."""

    value: T | None
    benchmark: BenchmarkRecord


def measure_call(
    algorithm: str,
    operation: Callable[[], T],
    *,
    result_counter: Callable[[T], int] = len,
) -> MeasuredResult[T]:
    """Execute an operation and honestly record success or failure metadata."""
    process = psutil.Process()
    before = process.memory_info().rss
    started = perf_counter()
    try:
        value = operation()
        status = "success"
        result_count = int(result_counter(value))
        error_type = ""
        error_message = ""
    except Exception as exc:  # Recorded for guarded experiments; callers may re-raise.
        value = None
        status = "failed"
        result_count = 0
        error_type = type(exc).__name__
        error_message = str(exc)
    elapsed = perf_counter() - started
    after = process.memory_info().rss
    record = BenchmarkRecord(
        algorithm=algorithm,
        status=status,
        runtime_seconds=elapsed,
        rss_before_bytes=before,
        rss_after_bytes=after,
        rss_delta_bytes=after - before,
        result_count=result_count,
        error_type=error_type,
        error_message=error_message,
    )
    return MeasuredResult(value=value, benchmark=record)
