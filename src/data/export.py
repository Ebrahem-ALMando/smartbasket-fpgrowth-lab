"""Stable export helpers for generated data artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def save_csv(frame: pd.DataFrame, path: Path, *, index: bool = False) -> None:
    """Write a UTF-8 CSV after creating its parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=index, encoding="utf-8", lineterminator="\n")


def save_json(value: Any, path: Path) -> None:
    """Write deterministic, human-readable UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
