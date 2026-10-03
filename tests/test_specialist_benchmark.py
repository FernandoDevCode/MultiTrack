from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from stemlab.app.specialist_benchmark import (
    _write_json_atomic,
    run_specialist_benchmark,
)


def _write_tone(path: Path, *, seconds: float = 0.25, sample_rate: int = 44_100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * sample_rate)
    time = np.arange(frames, dtype=np.float32) / sample_rate
    mono = 0.1 * np.sin(2 * np.pi * 220 * time)
    sf.write(path, np.column_stack((mono, mono)), sample_rate, subtype="PCM_16")


def _fake_result(stage: str, input_path: Path, output_dir: Path) -> dict:
    roles = {
        "core": ("vocals", "drums", "bass", "guitar", "piano", "other"),
        "g1": ("lead", "rhythm"),
        "g2": ("lead", "rhythm"),
        "b1": ("bass", "other"),
    }[stage]
    output_dir.mkdir(parents=True)
    stems = []
    for role in roles:
        path = output_dir / f"fixture_({role})_model.wav"
        _write_tone(path)
        stems.append({"role": role, "path": str(path.resolve())})
    return {
        "success": True,
        "input": {"path": str(input_path.resolve())},
        "model": {"model_id": stage},
        "backend": "fake",
        "device": {
            "effective_device": "cuda",
            "effective_precision": "autocast",
            "peak_cuda_allocated_bytes": 10,
            "peak_cuda_reserved_bytes": 20,
        },
        "timings": {"total_seconds": 1.0},
        "stems": stems,
        "warnings": [],
    }


def test_harness_reuses_core_and_preserves_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "song.wav"
    _write_tone(input_path)
    original = input_path.read_bytes()
    calls = []

    monkeypatch.setattr(
        "stemlab.app.specialist_benchmark.verify_all_specialist_candidates",
        lambda models_dir: (),
    )

    def runner(**kwargs):
        calls.append((kwargs["stage"], kwargs["input_path"]))
        return _fake_result(
            kwargs["stage"], kwargs["input_path"], kwargs["output_dir"]
        )

    manifest_path, manifest = run_specialist_benchmark(
        repo_root=tmp_path,
        input_path=input_path,
        run_id="unit-run",
        stage_runner=runner,
    )

    assert [stage for stage, _ in calls] == ["core", "g1", "g2", "b1"]
    assert sum(stage == "core" for stage, _ in calls) == 1
    assert calls[2][1].name == "G0_core_guitar.wav"
    assert input_path.read_bytes() == original
    assert manifest["input"]["sha256_before"] == manifest["input"]["sha256_after"]
    assert manifest["core_reuse"]["G0_and_B0_from_same_run"] is True
    assert len(manifest["outputs"]) == 7
    assert not (manifest_path.parent / ".stages").exists()
    assert {item["name"] for item in manifest["outputs"]} == {
        "G0_core_guitar",
        "G1_direct_lead",
        "G1_direct_rhythm",
        "G2_twostage_lead",
        "G2_twostage_rhythm",
        "B0_core_bass",
        "B1_specialist_bass",
    }


def test_failed_variant_records_error_without_hidden_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "song.wav"
    _write_tone(input_path)
    calls = []
    monkeypatch.setattr(
        "stemlab.app.specialist_benchmark.verify_all_specialist_candidates",
        lambda models_dir: (),
    )

    def runner(**kwargs):
        calls.append(kwargs["stage"])
        if kwargs["stage"] == "g1":
            return {
                "success": False,
                "error": {"message": "intentional failure"},
            }
        return _fake_result(
            kwargs["stage"], kwargs["input_path"], kwargs["output_dir"]
        )

    with pytest.raises(RuntimeError, match="no fallback"):
        run_specialist_benchmark(
            repo_root=tmp_path,
            input_path=input_path,
            run_id="failed-run",
            stage_runner=runner,
        )

    assert calls == ["core", "g1"]
    manifest_path = tmp_path / "bench/private/song/failed-run/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "FAILED"
    assert manifest["errors"][0]["stage"] == "g1"


def test_output_validation_rejects_silent_published_stem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "song.wav"
    _write_tone(input_path)
    monkeypatch.setattr(
        "stemlab.app.specialist_benchmark.verify_all_specialist_candidates",
        lambda models_dir: (),
    )

    def runner(**kwargs):
        result = _fake_result(
            kwargs["stage"], kwargs["input_path"], kwargs["output_dir"]
        )
        if kwargs["stage"] == "b1":
            bass = next(item for item in result["stems"] if item["role"] == "bass")
            sf.write(bass["path"], np.zeros((11_025, 2), dtype=np.float32), 44_100)
        return result

    with pytest.raises(RuntimeError, match="silent"):
        run_specialist_benchmark(
            repo_root=tmp_path,
            input_path=input_path,
            run_id="silent-run",
            stage_runner=runner,
        )


def test_manifest_writer_is_deterministic_and_json_serializable(tmp_path: Path) -> None:
    payload = {"z": [3, 2, 1], "a": {"value": True}}
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    _write_json_atomic(first, payload)
    _write_json_atomic(second, payload)

    assert first.read_bytes() == second.read_bytes()
    assert json.loads(first.read_text(encoding="utf-8")) == payload
