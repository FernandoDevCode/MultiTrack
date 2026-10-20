from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from stemlab.domain import (
    AudioMetadata,
    DevicePolicy,
    ModelSpec,
    OutputFormat,
    SeparationRequest,
)
from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend


def _request(
    tmp_path: Path,
    policy: DevicePolicy,
    output_format: OutputFormat = OutputFormat.WAV,
) -> SeparationRequest:
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    return SeparationRequest(
        input_path=tmp_path / "input.wav",
        model=ModelSpec(
            model_id="core-test",
            checkpoint_path=models_dir / "model.ckpt",
            expected_sha256="a" * 64,
        ),
        output_dir=tmp_path / "outputs",
        output_format=output_format,
        device_policy=policy,
        use_autocast=True,
    )


def _metadata(tmp_path: Path) -> AudioMetadata:
    return AudioMetadata(
        path=tmp_path / "input.wav",
        format="WAV",
        subtype="FLOAT",
        frames=100,
        duration_seconds=0.1,
        sample_rate=1000,
        channels=2,
        bytes=100,
        sha256="b" * 64,
    )


class FakeSeparator:
    def __init__(self, device: str, *, precision: str, failure: Exception | None = None):
        self.torch_device = torch.device(device)
        self.model_instance = None
        self.effective_precision = precision
        self.failure = failure
        self.separate_calls = 0

    def load_model(self, _filename: str) -> None:
        self.model_instance = SimpleNamespace(torch_device=self.torch_device)

    def separate(self, _input: str) -> list[str]:
        self.separate_calls += 1
        if self.failure:
            raise self.failure
        return ["song_(Vocals)_model.wav"]


def _run_with_fake(
    tmp_path: Path,
    monkeypatch,
    *,
    policy: DevicePolicy,
    cuda_available: bool,
    fake_device: str,
    precision: str,
    failure: Exception | None = None,
):
    backend = AudioSeparatorBackend(models_dir=tmp_path / "models")
    fake = FakeSeparator(fake_device, precision=precision, failure=failure)
    captured: dict = {}

    def separator_for(_specialist, kwargs):
        captured.update(kwargs)
        return fake

    monkeypatch.setattr(torch.cuda, "is_available", lambda: cuda_available)
    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: None)
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", lambda: None)
    monkeypatch.setattr(torch.cuda, "synchronize", lambda: None)
    monkeypatch.setattr(torch.cuda, "max_memory_allocated", lambda: 1)
    monkeypatch.setattr(torch.cuda, "max_memory_reserved", lambda: 2)
    monkeypatch.setattr(backend, "_separator_for", separator_for)
    result = backend.separate(_request(tmp_path, policy), _metadata(tmp_path))
    return result, captured, fake


@pytest.mark.parametrize(
    "policy,cuda_available,fake_device,precision,expected_autocast",
    [
        (DevicePolicy.AUTO, False, "cpu", "fp32", False),
        (DevicePolicy.AUTO, True, "cuda", "autocast", True),
        (DevicePolicy.CUDA_REQUIRED, True, "cuda", "autocast", True),
        (DevicePolicy.CPU_REQUIRED, True, "cpu", "fp32", False),
    ],
)
def test_device_policy_selects_exact_device_and_cpu_fp32(
    tmp_path: Path,
    monkeypatch,
    policy: DevicePolicy,
    cuda_available: bool,
    fake_device: str,
    precision: str,
    expected_autocast: bool,
) -> None:
    result, captured, fake = _run_with_fake(
        tmp_path,
        monkeypatch,
        policy=policy,
        cuda_available=cuda_available,
        fake_device=fake_device,
        precision=precision,
    )
    assert result.effective_device == fake_device
    assert result.effective_precision == precision
    assert captured["use_autocast"] is expected_autocast
    assert fake.separate_calls == 1
    if fake_device == "cpu":
        assert any("can be slow" in warning for warning in result.warnings)


def test_mp3_output_uses_explicit_ffmpeg_route_at_320k(
    tmp_path: Path, monkeypatch
) -> None:
    backend = AudioSeparatorBackend(models_dir=tmp_path / "models")
    fake = FakeSeparator("cpu", precision="fp32")
    captured: dict = {}

    def separator_for(_specialist, kwargs):
        captured.update(kwargs)
        return fake

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(backend, "_separator_for", separator_for)
    backend.separate(
        _request(tmp_path, DevicePolicy.AUTO, OutputFormat.MP3),
        _metadata(tmp_path),
    )

    assert captured["output_format"] == "MP3"
    assert captured["output_bitrate"] == "320k"
    assert captured["use_soundfile"] is False


def test_cuda_required_without_cuda_fails_without_cpu_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    backend = AudioSeparatorBackend(models_dir=tmp_path / "models")
    with pytest.raises(Exception, match="CUDA was required"):
        backend.separate(
            _request(tmp_path, DevicePolicy.CUDA_REQUIRED), _metadata(tmp_path)
        )


def test_policy_rejects_effective_device_mismatch(tmp_path: Path, monkeypatch) -> None:
    with pytest.raises(Exception, match="violates the requested policy"):
        _run_with_fake(
            tmp_path,
            monkeypatch,
            policy=DevicePolicy.CPU_REQUIRED,
            cuda_available=True,
            fake_device="cuda",
            precision="autocast",
        )


def test_auto_cuda_oom_is_not_retried_on_cpu(tmp_path: Path, monkeypatch) -> None:
    backend = AudioSeparatorBackend(models_dir=tmp_path / "models")
    fake = FakeSeparator(
        "cuda", precision="autocast", failure=torch.cuda.OutOfMemoryError("oom")
    )
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: None)
    monkeypatch.setattr(torch.cuda, "reset_peak_memory_stats", lambda: None)
    monkeypatch.setattr(torch.cuda, "synchronize", lambda: None)
    monkeypatch.setattr(backend, "_separator_for", lambda _specialist, _kwargs: fake)

    with pytest.raises(Exception, match="ran out of memory"):
        backend.separate(_request(tmp_path, DevicePolicy.AUTO), _metadata(tmp_path))
    assert fake.separate_calls == 1


def test_cpu_entrypoints_hide_cuda_before_adapter_import() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative in ("src/stemlab/workers/run_job.py", "src/stemlab/cli.py"):
        source = (root / relative).read_text(encoding="utf-8")
        assert source.index('os.environ["CUDA_VISIBLE_DEVICES"] = "-1"') < source.index(
            "from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend"
        )
