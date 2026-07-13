"""Runtime metadata validation and cautious summary helpers."""

from __future__ import annotations

import pandas as pd


RUNTIME_COLUMNS = {
    "environment", "implementation", "run_kind", "run_number", "status",
    "startup_seconds", "loading_seconds", "mining_seconds", "export_seconds",
    "end_to_end_seconds", "approximate_memory_bytes", "startup_included",
    "loading_included", "mining_included",
}


def validate_runtime_metadata(runs: pd.DataFrame) -> None:
    """Require explicit inclusion semantics for every timing record."""
    missing = RUNTIME_COLUMNS.difference(runs.columns)
    if missing:
        raise ValueError(f"Runtime table is missing columns: {sorted(missing)}")
    if runs.empty or (runs["status"] != "success").any():
        raise ValueError("Runtime comparison contains no successful complete run set")
    if runs[["loading_seconds", "mining_seconds", "end_to_end_seconds"]].isna().any(axis=None):
        raise ValueError("Runtime comparison contains missing required timings")


def summarize_runtime(runs: pd.DataFrame) -> pd.DataFrame:
    """Summarize measured runs only; warm-up remains visible in the raw table."""
    validate_runtime_metadata(runs)
    measured = runs.loc[runs["run_kind"] == "measured"]
    return (
        measured.groupby("implementation", sort=True)
        .agg(
            measured_runs=("run_number", "count"),
            median_loading_seconds=("loading_seconds", "median"),
            median_mining_seconds=("mining_seconds", "median"),
            median_end_to_end_seconds=("end_to_end_seconds", "median"),
            median_startup_seconds=("startup_seconds", "median"),
            maximum_approximate_memory_bytes=("approximate_memory_bytes", "max"),
        )
        .reset_index()
    )

