from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnalysisLaunch:
    input_path: Path


def build_analysis_worker_command(repo_root: Path, launch: AnalysisLaunch) -> tuple[str, list[str]]:
    root = repo_root.resolve()
    return (
        str(root / ".venv" / "Scripts" / "python.exe"),
        [
            "-X",
            "utf8",
            "-m",
            "stemlab.workers.run_analysis",
            "--input",
            str(launch.input_path.resolve()),
        ],
    )
