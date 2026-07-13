"""Discovery and reproducible invocation helpers for project-local WEKA."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class WekaEnvironment:
    java_executable: str
    javac_executable: str | None
    java_version: str
    java_vendor: str
    java_architecture: str
    weka_version: str
    weka_jar: str
    weka_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=True)


def inspect_environment(
    *, java_path: Path, weka_jar: Path, javac_path: Path | None = None
) -> WekaEnvironment:
    """Inspect only explicitly supplied official distribution executables."""
    version = _run([str(java_path), "-version"])
    version_text = (version.stderr or version.stdout).strip()
    properties = _run([str(java_path), "-XshowSettings:properties", "-version"])
    property_text = (properties.stderr or "") + "\n" + (properties.stdout or "")
    vendor = re.search(r"^\s*java\.vendor\s*=\s*(.+)$", property_text, re.MULTILINE)
    architecture = re.search(r"^\s*os\.arch\s*=\s*(.+)$", property_text, re.MULTILINE)
    weka = _run([str(java_path), "-cp", str(weka_jar), "weka.core.Version"])
    return WekaEnvironment(
        java_executable=str(java_path),
        javac_executable=str(javac_path) if javac_path and javac_path.exists() else None,
        java_version=version_text.splitlines()[0],
        java_vendor=vendor.group(1).strip() if vendor else "unavailable",
        java_architecture=architecture.group(1).strip() if architecture else platform.machine(),
        weka_version=weka.stdout.strip().splitlines()[0],
        weka_jar=str(weka_jar),
        weka_sha256=sha256_file(weka_jar),
    )


def save_environment(environment: WekaEnvironment, path: Path, project_root: Path) -> None:
    """Save environment metadata with project-relative executable paths."""
    document = asdict(environment)
    for key in ("java_executable", "javac_executable", "weka_jar"):
        if document[key]:
            document[key] = Path(str(document[key])).resolve().relative_to(project_root).as_posix()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
