from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


def test_existing_roformer_runs_through_phase1_service(tmp_path: Path) -> None:
    if os.environ.get("STEMLAB_RUN_GPU_SMOKE") != "1":
        pytest.skip("set STEMLAB_RUN_GPU_SMOKE=1 to run the existing checkpoint")

    from stemlab.app import SeparationService
    from stemlab.domain import DevicePolicy, ModelSpec, SeparationRequest
    from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend

    repo_root = Path(__file__).resolve().parents[2]
    phase0 = json.loads(
        (repo_root / ".tmp" / "phase0-smoke" / "latest-result.json").read_text(
            encoding="utf-8"
        )
    )
    input_path = Path(phase0["input"]["path"])
    output_dir = tmp_path / "outputs"
    model_path = repo_root / "models" / "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
    config_path = repo_root / "models" / "model_bs_roformer_ep_317_sdr_12.9755.yaml"
    request = SeparationRequest(
        input_path=input_path,
        model=ModelSpec(
            model_id="bs-roformer-viperx-1297-experimental-smoke",
            checkpoint_path=model_path,
            expected_sha256="5b84f37e8d444c8cb30c79d77f613a41c05868ff9c9ac6c7049c00aefae115aa",
            config_paths=(config_path,),
            expected_config_sha256=(
                "2bfdd16c656bd9519aba757cc4f8834b7ede675eb1e00ec4772d74ae1c41af7f",
            ),
        ),
        output_dir=output_dir,
        device_policy=DevicePolicy.CUDA_REQUIRED,
    )
    backend = AudioSeparatorBackend(
        models_dir=repo_root / "models",
        ffmpeg_bin=repo_root / "tools" / "ffmpeg" / "bin",
    )

    result = SeparationService(backend).separate(request)

    assert result.success, result.error
    assert result.device and result.device.effective_device == "cuda"
    assert result.device.peak_cuda_allocated_bytes
    assert len(result.stems) == 2
    assert {stem.role for stem in result.stems} == {"vocals", "instrumental"}
