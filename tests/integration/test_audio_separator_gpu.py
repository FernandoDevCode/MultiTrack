from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


def test_six_stem_roformer_runs_through_phase1_service(tmp_path: Path) -> None:
    if os.environ.get("STEMLAB_RUN_GPU_SMOKE") != "1":
        pytest.skip("set STEMLAB_RUN_GPU_SMOKE=1 to run the existing checkpoint")

    from stemlab.app import SIX_STEMS, SeparationService, build_request
    from stemlab.domain import OutputFormat
    from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend

    repo_root = Path(__file__).resolve().parents[2]
    phase0 = json.loads(
        (repo_root / ".tmp" / "phase0-smoke" / "latest-result.json").read_text(
            encoding="utf-8"
        )
    )
    input_path = Path(phase0["input"]["path"])
    output_dir = tmp_path / "outputs"
    request = build_request(
        repo_root=repo_root,
        input_path=input_path,
        mode_id=SIX_STEMS.mode_id,
        output_dir=output_dir,
        output_format=OutputFormat.WAV,
    )
    backend = AudioSeparatorBackend(
        models_dir=repo_root / "models",
        ffmpeg_bin=repo_root / "tools" / "ffmpeg" / "bin",
    )

    result = SeparationService(backend).separate(request)

    assert result.success, result.error
    assert result.device and result.device.effective_device == "cuda"
    assert result.device.peak_cuda_allocated_bytes
    assert {stem.role for stem in result.stems} == set(SIX_STEMS.expected_roles)
