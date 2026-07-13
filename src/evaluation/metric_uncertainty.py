"""Transparent empirical metric-uncertainty summaries for Bootstrap observations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def metric_interval(values: pd.Series) -> dict[str, float | int]:
    """Return finite-observation mean, sample SD, percentiles, and extrema."""
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    finite = numeric[np.isfinite(numeric)]
    if finite.size == 0:
        return {
            "valid_observations": 0,
            "mean": np.nan,
            "std": np.nan,
            "p025": np.nan,
            "p975": np.nan,
            "minimum": np.nan,
            "maximum": np.nan,
        }
    return {
        "valid_observations": int(finite.size),
        "mean": float(finite.mean()),
        "std": float(finite.std(ddof=1)) if finite.size > 1 else 0.0,
        "p025": float(np.percentile(finite, 2.5)),
        "p975": float(np.percentile(finite, 97.5)),
        "minimum": float(finite.min()),
        "maximum": float(finite.max()),
    }
