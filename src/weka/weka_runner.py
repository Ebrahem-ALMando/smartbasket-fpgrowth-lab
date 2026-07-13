"""Reproducible bridge/CLI execution and repeated Python–WEKA timings."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import psutil

from src.data.basket_matrix import BasketArtifacts, to_pandas_sparse_frame
from src.data.weka_export import load_frozen_basket
from src.mining.fpgrowth_runner import run_fpgrowth
from src.mining.rule_generation import generate_rules


@dataclass(frozen=True)
class JavaPaths:
    java: Path
    weka_jar: Path
    classes: Path
    weka_home: Path


def _classpath(paths: JavaPaths) -> str:
    return os.pathsep.join((str(paths.classes.resolve()), str(paths.weka_jar.resolve())))


def run_bridge_once(
    paths: JavaPaths,
    arff: Path,
    output_directory: Path,
    *,
    label: str,
    timeout_seconds: float = 300.0,
) -> dict[str, object]:
    """Run one fresh JVM bridge process and retain all process evidence."""
    output_directory.mkdir(parents=True, exist_ok=True)
    files = {
        "rules": output_directory / f"{label}_rules.csv",
        "console": output_directory / f"{label}_console.txt",
        "metadata": output_directory / f"{label}_metadata.json",
        "options": output_directory / f"{label}_options.json",
        "stdout": output_directory / f"{label}_stdout.txt",
        "stderr": output_directory / f"{label}_stderr.txt",
    }
    command = [
        str(paths.java), "--add-opens=java.base/java.lang=ALL-UNNAMED",
        "-Xmx4g", f"-DWEKA_HOME={paths.weka_home.resolve()}",
        "-cp", _classpath(paths), "WekaFPGrowthBridge", str(arff.resolve()),
        str(files["rules"].resolve()), str(files["console"].resolve()),
        str(files["metadata"].resolve()), str(files["options"].resolve()),
    ]
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
    wall = time.perf_counter() - started
    files["stdout"].write_text(completed.stdout, encoding="utf-8")
    files["stderr"].write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"WEKA bridge failed ({completed.returncode}): {completed.stderr[-2000:]}")
    metadata = json.loads(files["metadata"].read_text(encoding="utf-8"))
    metadata.update(
        {
            "label": label,
            "process_wall_seconds": wall,
            "approximate_startup_seconds": max(0.0, wall - float(metadata["bridge_total_seconds"])),
            "exit_code": completed.returncode,
            "exact_command": command,
            "stdout_path": files["stdout"].as_posix(),
            "stderr_path": files["stderr"].as_posix(),
        }
    )
    return {"metadata": metadata, "files": files}


def benchmark_weka_bridge(
    paths: JavaPaths,
    arff: Path,
    scratch_directory: Path,
    final_directory: Path,
) -> pd.DataFrame:
    """Execute one warm-up and three fresh measured JVM bridge runs."""
    records: list[dict[str, object]] = []
    completed_runs: list[dict[str, object]] = []
    for run_number in range(4):
        kind = "warmup" if run_number == 0 else "measured"
        label = f"weka_{kind}_{run_number}"
        result = run_bridge_once(paths, arff, scratch_directory, label=label)
        completed_runs.append(result)
        metadata = result["metadata"]
        records.append(
            {
                "environment": "BellSoft OpenJDK 25.0.2 / WEKA 3.8.7 / sparse ARFF",
                "implementation": "WEKA",
                "run_kind": kind,
                "run_number": run_number,
                "status": metadata["status"],
                "startup_seconds": metadata["approximate_startup_seconds"],
                "loading_seconds": metadata["loading_seconds"],
                "mining_seconds": metadata["mining_seconds"],
                "export_seconds": metadata["rule_export_seconds"],
                "end_to_end_seconds": metadata["process_wall_seconds"],
                "approximate_memory_bytes": metadata["approximate_jvm_used_memory_bytes"],
                "startup_included": True,
                "loading_included": True,
                "mining_included": True,
                "rule_count": metadata["rule_count"],
            }
        )
    primary = completed_runs[-1]
    final_directory.mkdir(parents=True, exist_ok=True)
    destinations = {
        "rules": "weka_rules_raw.csv", "console": "weka_console_output.txt",
        "metadata": "weka_run_metadata.json", "options": "weka_effective_options.json",
        "stdout": "weka_bridge_stdout.txt", "stderr": "weka_bridge_stderr.txt",
    }
    for key, name in destinations.items():
        shutil.copy2(primary["files"][key], final_directory / name)
    final_metadata = primary["metadata"].copy()
    final_metadata["exact_command"] = [
        value.replace(str(Path.cwd().resolve()), ".") for value in final_metadata["exact_command"]
    ]
    final_metadata["stdout_path"] = "weka/results/weka_bridge_stdout.txt"
    final_metadata["stderr_path"] = "weka/results/weka_bridge_stderr.txt"
    (final_directory / "weka_run_metadata.json").write_text(
        json.dumps(final_metadata, indent=2) + "\n", encoding="utf-8"
    )
    return pd.DataFrame(records)


def benchmark_python(
    matrix_path: Path,
    columns_path: Path,
    transactions_path: Path,
) -> pd.DataFrame:
    """Run one warm-up plus three full aligned Python mining measurements."""
    process = psutil.Process()
    records: list[dict[str, object]] = []
    for run_number in range(4):
        kind = "warmup" if run_number == 0 else "measured"
        total_start = time.perf_counter()
        load_start = time.perf_counter()
        matrix, columns, transactions = load_frozen_basket(
            matrix_path, columns_path, transactions_path
        )
        basket = to_pandas_sparse_frame(BasketArtifacts(matrix, transactions, columns))
        loading = time.perf_counter() - load_start
        rss_before = process.memory_info().rss
        mining_start = time.perf_counter()
        patterns = run_fpgrowth(basket, minimum_support=0.005, maximum_length=3)
        descriptions = dict(zip(columns["StockCode"].astype(str), columns["Description"].astype(str)))
        rules = generate_rules(
            patterns.itemsets, transaction_count=matrix.shape[0], descriptions=descriptions,
            minimum_confidence=0.70,
        )
        mining = time.perf_counter() - mining_start
        total = time.perf_counter() - total_start
        rss_after = process.memory_info().rss
        records.append(
            {
                "environment": "Python 3.11.9 / mlxtend 0.25.0 / pandas sparse",
                "implementation": "Python", "run_kind": kind, "run_number": run_number,
                "status": "success", "startup_seconds": 0.0,
                "loading_seconds": loading, "mining_seconds": mining, "export_seconds": 0.0,
                "end_to_end_seconds": total,
                "approximate_memory_bytes": max(rss_before, rss_after),
                "startup_included": False, "loading_included": True, "mining_included": True,
                "rule_count": len(rules),
            }
        )
    return pd.DataFrame(records)


def run_official_cli(
    paths: JavaPaths,
    arff: Path,
    output_directory: Path,
    *,
    timeout_seconds: float = 300.0,
) -> dict[str, object]:
    """Run official FPGrowth CLI with help-verified aligned options."""
    output_directory.mkdir(parents=True, exist_ok=True)
    command = [
        str(paths.java), "--add-opens=java.base/java.lang=ALL-UNNAMED",
        "-Xmx4g", f"-DWEKA_HOME={paths.weka_home.resolve()}",
        "-cp", str(paths.weka_jar.resolve()), "weka.associations.FPGrowth",
        "-t", str(arff.resolve()), "-P", "2", "-I", "3", "-N", "1000000",
        "-T", "0", "-C", "0.70", "-U", "1.0", "-M", "0.005",
        "-D", "0.005", "-S",
    ]
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
    wall = time.perf_counter() - started
    (output_directory / "weka_cli_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_directory / "weka_cli_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    metadata = {
        "status": "success" if completed.returncode == 0 else "failure",
        "exit_code": completed.returncode,
        "wall_clock_seconds": wall,
        "java_version": "BellSoft OpenJDK 25.0.2+12 LTS",
        "weka_version": "3.8.7",
        "exact_command": [value.replace(str(Path.cwd().resolve()), ".") for value in command],
        "stdout": "weka/results/weka_cli_stdout.txt",
        "stderr": "weka/results/weka_cli_stderr.txt",
    }
    (output_directory / "weka_cli_run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Official WEKA CLI failed: {completed.stderr[-2000:]}")
    return metadata
