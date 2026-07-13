"""Portable project path helpers."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_path(*parts: str) -> Path:
    """Return a resolved path contained within the project root."""
    candidate = PROJECT_ROOT.joinpath(*parts).resolve()
    if not candidate.is_relative_to(PROJECT_ROOT):
        raise ValueError(f"Path escapes the project root: {candidate}")
    return candidate


def ensure_directory(*parts: str) -> Path:
    """Create and return a project-relative directory safely."""
    directory = project_path(*parts)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
