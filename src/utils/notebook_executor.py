"""Execute Phase 3 notebooks reproducibly and record execution evidence."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import nbformat
import pandas as pd
from nbclient import NotebookClient

from src.data.export import save_csv
from src.data.paths import PROJECT_ROOT, project_path


PHASE_3_NOTEBOOKS = (
    project_path("notebooks", "01_project_introduction.ipynb"),
    project_path("notebooks", "03_data_preparation.ipynb"),
)
PHASE_4_NOTEBOOKS = (
    project_path("notebooks", "02_manual_fp_tree_example.ipynb"),
    project_path("notebooks", "04_fpgrowth_analysis.ipynb"),
    project_path("notebooks", "05_apriori_comparison.ipynb"),
)


def _clear_execution_state(notebook: nbformat.NotebookNode) -> None:
    """Remove prior code outputs so every run starts from clean notebook state."""
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.execution_count = None
            cell.outputs = []


def execute_notebook(path: Path) -> dict[str, object]:
    """Execute one notebook in a fresh kernel rooted at the project directory."""
    notebook = nbformat.read(path, as_version=4)
    _clear_execution_state(notebook)
    started = perf_counter()

    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        resources={"metadata": {"path": str(PROJECT_ROOT)}},
        allow_errors=False,
    )
    client.execute()
    duration = perf_counter() - started
    nbformat.write(notebook, path)

    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    error_count = sum(
        output.output_type == "error"
        for cell in code_cells
        for output in cell.get("outputs", [])
    )
    return {
        "notebook": path.name,
        "status": "success",
        "code_cell_count": len(code_cells),
        "executed_code_cell_count": sum(
            cell.get("execution_count") is not None for cell in code_cells
        ),
        "error_count": error_count,
        "duration_seconds": round(duration, 3),
        "file_size_bytes": path.stat().st_size,
        "kernel": "python3 (.venv)",
        "working_directory": ".",
    }


def execute_phase3_notebooks() -> pd.DataFrame:
    """Execute both Phase 3 notebooks, each with its own clean kernel."""
    records = [execute_notebook(path) for path in PHASE_3_NOTEBOOKS]
    summary = pd.DataFrame.from_records(records)
    save_csv(
        summary,
        project_path("outputs", "tables", "notebook_execution_summary.csv"),
    )
    return summary


def execute_phase4_notebooks() -> pd.DataFrame:
    """Execute all Phase 4 notebooks and append/upsert their evidence."""
    records = [execute_notebook(path) for path in PHASE_4_NOTEBOOKS]
    phase4 = pd.DataFrame.from_records(records)
    summary_path = project_path("outputs", "tables", "notebook_execution_summary.csv")
    if summary_path.exists():
        existing = pd.read_csv(summary_path)
        existing = existing.loc[~existing["notebook"].isin(phase4["notebook"])]
        combined = pd.concat([existing, phase4], ignore_index=True)
    else:
        combined = phase4
    save_csv(combined, summary_path)
    return phase4


if __name__ == "__main__":
    print(execute_phase4_notebooks().to_string(index=False))
