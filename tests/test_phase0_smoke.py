from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = REPO_ROOT / ".tmp" / "phase0-smoke" / "latest-result.json"


def test_latest_model_smoke_evidence() -> None:
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))

    assert result["status"] == "PASS"
    assert result["model"]["architecture"] == "BS-RoFormer / audio-separator MDXC"
    assert result["model"]["status"] == "experimental-smoke-only"
    assert result["runtime"]["device"] == "NVIDIA GeForce RTX 5060"
    assert result["runtime"]["separator_device"] == "cuda"
    assert result["runtime"]["model_device"] == "cuda"
    assert result["runtime"]["peak_cuda_allocated_bytes"] > 0
    assert result["runtime"]["peak_cuda_reserved_bytes"] > 0
    assert len(result["outputs"]) == 2

    input_duration = result["input"]["duration_seconds"]
    for output in result["outputs"]:
        assert Path(output["path"]).is_file()
        assert output["bytes"] > 44
        assert output["sample_rate"] == 44_100
        assert output["channels"] == 2
        assert abs(output["duration_seconds"] - input_duration) <= 0.1
        assert output["rms"] > 1e-4
        assert output["peak"] > 1e-3
