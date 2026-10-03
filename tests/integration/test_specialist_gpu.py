from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

from stemlab.app.specialist_benchmark import (
    run_specialist_benchmark,
    run_stage_subprocess,
)


pytestmark = pytest.mark.integration


def _smoke_input(repo_root: Path) -> Path:
    phase0 = json.loads(
        (repo_root / ".tmp" / "phase0-smoke" / "latest-result.json").read_text(
            encoding="utf-8"
        )
    )
    return Path(phase0["input"]["path"])


@pytest.mark.parametrize(
    ("stage", "expected_roles"),
    [
        ("g1", {"lead", "rhythm"}),
        ("b1", {"bass", "other"}),
    ],
)
def test_specialist_candidate_cuda_offline(
    tmp_path: Path, stage: str, expected_roles: set[str]
) -> None:
    if os.environ.get("STEMLAB_RUN_SPECIALIST_SMOKE") != "1":
        pytest.skip("set STEMLAB_RUN_SPECIALIST_SMOKE=1 to run specialist CUDA smokes")
    repo_root = Path(__file__).resolve().parents[2]

    result = run_stage_subprocess(
        repo_root=repo_root,
        stage=stage,
        input_path=_smoke_input(repo_root),
        output_dir=tmp_path / stage,
    )

    assert result["success"], result.get("error")
    assert result["device"]["effective_device"] == "cuda"
    assert result["device"]["peak_cuda_allocated_bytes"] > 0
    assert result["device"]["peak_cuda_reserved_bytes"] > 0
    assert {stem["role"] for stem in result["stems"]} == expected_roles


def test_full_specialist_harness_cuda_offline() -> None:
    if os.environ.get("STEMLAB_RUN_SPECIALIST_HARNESS_SMOKE") != "1":
        pytest.skip(
            "set STEMLAB_RUN_SPECIALIST_HARNESS_SMOKE=1 to run the complete harness"
        )
    repo_root = Path(__file__).resolve().parents[2]

    manifest_path, manifest = run_specialist_benchmark(
        repo_root=repo_root,
        input_path=_smoke_input(repo_root),
        run_id=f"technical-smoke-{uuid4().hex[:10]}",
    )

    assert manifest_path.is_file()
    assert manifest["status"] == "PASS"
    assert manifest["input"]["sha256_before"] == manifest["input"]["sha256_after"]
    assert [item["stage"] for item in manifest["stages"]] == [
        "core",
        "g1",
        "g2",
        "b1",
    ]
    assert len(manifest["outputs"]) == 7
