from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from stemlab.app import SeparationService
from stemlab.audio import sha256_file
from stemlab.domain import (
    BackendSeparationError,
    DevicePolicy,
    DeviceUnavailableError,
    ModelSpec,
    SeparationRequest,
)
from stemlab.separation import BackendResult, BackendStem


class FakeBackend:
    def __init__(self, *, failure: Exception | None = None, outside: Path | None = None) -> None:
        self.failure = failure
        self.outside = outside
        self.calls = 0

    def separate(self, request, input_metadata):
        self.calls += 1
        if self.failure:
            raise self.failure
        output = self.outside or (request.output_dir / "fixture_(Vocals)_fake.wav")
        audio, rate = sf.read(request.input_path, dtype="float32", always_2d=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output, audio * 0.5, rate, subtype="FLOAT")
        return BackendResult(
            backend_id="fake/1",
            effective_device="cuda",
            effective_precision="float16",
            model_load_seconds=0.01,
            inference_seconds=0.02,
            total_seconds=0.03,
            stems=(BackendStem(role="vocals", path=output),),
            peak_cuda_allocated_bytes=123,
            peak_cuda_reserved_bytes=456,
        )


def _fixture(tmp_path: Path) -> tuple[SeparationRequest, Path]:
    input_path = tmp_path / "input.wav"
    samples = np.column_stack(
        [
            np.sin(np.linspace(0, 20, 4_410, dtype=np.float32)),
            np.cos(np.linspace(0, 20, 4_410, dtype=np.float32)),
        ]
    )
    sf.write(input_path, samples, 44_100, subtype="PCM_16")
    model_path = tmp_path / "models" / "model.ckpt"
    config_path = tmp_path / "models" / "model.yaml"
    model_path.parent.mkdir()
    model_path.write_bytes(b"approved fake checkpoint")
    config_path.write_text("model: fake\n", encoding="utf-8")
    request = SeparationRequest(
        input_path=input_path,
        model=ModelSpec(
            model_id="fake-test-model",
            checkpoint_path=model_path,
            expected_sha256=sha256_file(model_path),
            config_paths=(config_path,),
            expected_config_sha256=(sha256_file(config_path),),
        ),
        output_dir=tmp_path / "outputs",
        device_policy=DevicePolicy.CUDA_REQUIRED,
    )
    return request, input_path


def test_valid_separation_uses_injected_backend_and_writes_manifest(tmp_path: Path) -> None:
    request, input_path = _fixture(tmp_path)
    input_hash = sha256_file(input_path)
    backend = FakeBackend()

    result = SeparationService(backend).separate(request)

    assert result.success
    assert backend.calls == 1
    assert sha256_file(input_path) == input_hash
    assert result.backend == "fake/1"
    assert result.device and result.device.effective_device == "cuda"
    assert result.stems[0].role == "vocals"
    assert result.manifest_path and result.manifest_path.is_file()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["success"] is True
    assert manifest["input"]["sha256"] == input_hash
    assert manifest["model"]["model_id"] == "fake-test-model"
    assert manifest["stems"][0]["sha256"] == result.stems[0].sha256


def test_missing_input_is_structured_and_backend_is_not_called(tmp_path: Path) -> None:
    request, _ = _fixture(tmp_path)
    request = SeparationRequest(
        input_path=tmp_path / "missing.wav",
        model=request.model,
        output_dir=request.output_dir,
    )
    backend = FakeBackend()

    result = SeparationService(backend).separate(request)

    assert not result.success
    assert result.error and result.error.code == "input_not_found"
    assert backend.calls == 0


def test_missing_model_is_structured_and_backend_is_not_called(tmp_path: Path) -> None:
    request, _ = _fixture(tmp_path)
    request.model.checkpoint_path.unlink()
    backend = FakeBackend()

    result = SeparationService(backend).separate(request)

    assert not result.success
    assert result.error and result.error.code == "model_missing"
    assert backend.calls == 0


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (DeviceUnavailableError("CUDA unavailable"), "device_unavailable"),
        (BackendSeparationError("backend exploded"), "backend_separation"),
    ],
)
def test_backend_errors_are_propagated_as_structured_results(
    tmp_path: Path, failure: Exception, expected_code: str
) -> None:
    request, _ = _fixture(tmp_path)

    result = SeparationService(FakeBackend(failure=failure)).separate(request)

    assert not result.success
    assert result.error and result.error.code == expected_code
    assert result.manifest_path and result.manifest_path.is_file()


def test_model_hash_mismatch_prevents_backend_execution(tmp_path: Path) -> None:
    request, _ = _fixture(tmp_path)
    request.model.checkpoint_path.write_bytes(b"tampered")
    backend = FakeBackend()

    result = SeparationService(backend).separate(request)

    assert not result.success
    assert result.error and result.error.code == "model_integrity"
    assert backend.calls == 0


def test_backend_output_outside_requested_directory_is_rejected(tmp_path: Path) -> None:
    request, _ = _fixture(tmp_path)
    outside = tmp_path / "outside.wav"

    result = SeparationService(FakeBackend(outside=outside)).separate(request)

    assert not result.success
    assert result.error and result.error.code == "output_validation"


class InvalidStemBackend(FakeBackend):
    def separate(self, request, input_metadata):
        self.calls += 1
        output = request.output_dir / "invalid.wav"
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output, np.full((100, 2), np.nan, dtype=np.float32), 44_100, subtype="FLOAT")
        return BackendResult(
            backend_id="fake/invalid",
            effective_device="cuda",
            effective_precision="float16",
            model_load_seconds=0,
            inference_seconds=0,
            total_seconds=0,
            stems=(BackendStem(role="vocals", path=output),),
        )


def test_non_finite_stem_is_rejected(tmp_path: Path) -> None:
    request, _ = _fixture(tmp_path)

    result = SeparationService(InvalidStemBackend()).separate(request)

    assert not result.success
    assert result.error and result.error.code == "output_validation"
    assert "NaN or Inf" in result.error.message


class SilentStemBackend(FakeBackend):
    def separate(self, request, input_metadata):
        self.calls += 1
        output = request.output_dir / "silent.wav"
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(
            output,
            np.zeros((input_metadata.frames, input_metadata.channels), dtype=np.float32),
            input_metadata.sample_rate,
            subtype="FLOAT",
        )
        return BackendResult(
            backend_id="fake/silent",
            effective_device="cuda",
            effective_precision="float16",
            model_load_seconds=0,
            inference_seconds=0,
            total_seconds=0,
            stems=(BackendStem(role="vocals", path=output),),
        )


def test_silent_stem_is_rejected(tmp_path: Path) -> None:
    request, _ = _fixture(tmp_path)

    result = SeparationService(SilentStemBackend()).separate(request)

    assert not result.success
    assert result.error and result.error.code == "output_validation"
    assert result.error.message == "Stem is empty or silent."


def test_only_adapter_imports_audio_separator() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "stemlab"
    offenders = []
    for source in source_root.rglob("*.py"):
        if source.name == "audio_separator_adapter.py":
            continue
        text = source.read_text(encoding="utf-8")
        if "from audio_separator" in text or "import audio_separator" in text:
            offenders.append(source)
    assert offenders == []


def test_unexpected_stem_set_is_rejected(tmp_path: Path) -> None:
    request, _ = _fixture(tmp_path)
    request = SeparationRequest(
        input_path=request.input_path,
        model=request.model,
        output_dir=request.output_dir,
        expected_roles=("vocals", "instrumental"),
    )

    result = SeparationService(FakeBackend()).separate(request)

    assert not result.success
    assert result.error and result.error.code == "output_validation"
    assert result.error.details["actual_roles"] == ["vocals"]
