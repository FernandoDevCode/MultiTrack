from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest


pytestmark = pytest.mark.integration


def _phase0_input(repo_root: Path, phase0: dict) -> Path:
    recorded = Path(phase0["input"]["path"])
    if recorded.is_file():
        return recorded
    run_name = Path(phase0["run_dir"]).name
    relocated = repo_root / ".tmp" / "phase0-smoke" / run_name / recorded.name
    assert relocated.is_file(), f"Phase 0 fixture not found: {recorded} or {relocated}"
    return relocated


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
    input_path = _phase0_input(repo_root, phase0)
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


def _run_worker(
    repo_root: Path,
    input_path: Path,
    output_dir: Path,
    *,
    device: str,
    roles: tuple[str, ...],
) -> dict:
    command = [
        str(repo_root / ".venv" / "Scripts" / "python.exe"),
        "-X",
        "utf8",
        "-m",
        "stemlab.workers.run_job",
        "--input",
        str(input_path),
        "--mode",
        "six-stems",
        "--output",
        str(output_dir),
        "--format",
        "wav",
        "--device",
        device,
    ]
    for role in roles:
        command.extend(("--stem", role))
    environment = os.environ.copy()
    environment.update(
        {
            "TEMP": str(repo_root / ".tmp"),
            "TMP": str(repo_root / ".tmp"),
            "TORCH_HOME": str(repo_root / ".cache" / "torch"),
            "HF_HOME": str(repo_root / ".cache" / "huggingface"),
            "XDG_CACHE_HOME": str(repo_root / ".cache"),
            "MPLCONFIGDIR": str(repo_root / ".cache" / "matplotlib"),
            "AUDIO_SEPARATOR_MODEL_DIR": str(repo_root / "models"),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )
    if device == "cpu":
        environment["CUDA_VISIBLE_DEVICES"] = "-1"
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=900,
    )
    events = [
        json.loads(line[len("STEMLAB_EVENT ") :])
        for line in completed.stdout.splitlines()
        if line.startswith("STEMLAB_EVENT ")
    ]
    assert completed.returncode == 0, (events, completed.stderr[-4000:])
    completed_events = [event for event in events if event["type"] == "completed"]
    assert completed_events
    return completed_events[-1]["payload"]["result"]


def test_cpu_core_smoke_forced_fp32_in_worker(tmp_path: Path) -> None:
    if os.environ.get("STEMLAB_RUN_CPU_SMOKE") != "1":
        pytest.skip("set STEMLAB_RUN_CPU_SMOKE=1 to run the opt-in CPU Core smoke")
    repo_root = Path(__file__).resolve().parents[2]
    phase0 = json.loads(
        (repo_root / ".tmp" / "phase0-smoke" / "latest-result.json").read_text(
            encoding="utf-8"
        )
    )
    result = _run_worker(
        repo_root,
        _phase0_input(repo_root, phase0),
        tmp_path / "cpu-output",
        device="cpu",
        roles=("vocals",),
    )
    assert result["device"]["requested_policy"] == "cpu"
    assert result["device"]["effective_device"] == "cpu"
    assert result["device"]["effective_precision"] == "fp32"
    assert set(result["inferred_roles"]) == {
        "vocals", "drums", "bass", "guitar", "piano", "other"
    }
    assert result["produced_roles"] == ["vocals"]


def test_auto_with_cuda_hidden_selects_cpu_without_fallback(tmp_path: Path) -> None:
    if os.environ.get("STEMLAB_RUN_CPU_AUTO_SMOKE") != "1":
        pytest.skip("set STEMLAB_RUN_CPU_AUTO_SMOKE=1 to run AUTO with CUDA hidden")
    repo_root = Path(__file__).resolve().parents[2]
    phase0 = json.loads(
        (repo_root / ".tmp" / "phase0-smoke" / "latest-result.json").read_text(
            encoding="utf-8"
        )
    )
    previous = os.environ.get("CUDA_VISIBLE_DEVICES")
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    try:
        result = _run_worker(
            repo_root,
            _phase0_input(repo_root, phase0),
            tmp_path / "auto-cpu-output",
            device="auto",
            roles=("other",),
        )
    finally:
        if previous is None:
            os.environ.pop("CUDA_VISIBLE_DEVICES", None)
        else:
            os.environ["CUDA_VISIBLE_DEVICES"] = previous
    assert result["device"]["requested_policy"] == "auto"
    assert result["device"]["effective_device"] == "cpu"
    assert result["device"]["effective_precision"] == "fp32"
    assert result["produced_roles"] == ["other"]


def test_gpu_subset_smoke_retains_only_bass_and_guitar(tmp_path: Path) -> None:
    if os.environ.get("STEMLAB_RUN_GPU_SUBSET_SMOKE") != "1":
        pytest.skip("set STEMLAB_RUN_GPU_SUBSET_SMOKE=1 to run the GPU subset smoke")
    repo_root = Path(__file__).resolve().parents[2]
    phase0 = json.loads(
        (repo_root / ".tmp" / "phase0-smoke" / "latest-result.json").read_text(
            encoding="utf-8"
        )
    )
    result = _run_worker(
        repo_root,
        _phase0_input(repo_root, phase0),
        tmp_path / "gpu-subset-output",
        device="cuda",
        roles=("bass", "guitar"),
    )
    assert result["device"]["effective_device"] == "cuda"
    assert set(result["inferred_roles"]) == {
        "vocals", "drums", "bass", "guitar", "piano", "other"
    }
    assert result["requested_roles"] == ["bass", "guitar"]
    assert set(result["produced_roles"]) == {"bass", "guitar"}
    assert {stem["role"] for stem in result["stems"]} == {"bass", "guitar"}
    output_dir = Path(result["manifest_path"]).parent
    audio_files = {path.name for path in output_dir.glob("*.wav")}
    assert all("bass" in name.lower() or "guitar" in name.lower() for name in audio_files)
