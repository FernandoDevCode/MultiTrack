from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from stemlab.app import PROMPT_ALIASES, aggregate_instrument_evidence, plan_for_targets
from stemlab.app.audio_windows import MAX_WINDOWS, plan_analysis_windows
from stemlab.app.instrument_analysis_service import InstrumentationAnalysisService
from stemlab.audio import sha256_file
from stemlab.domain import CANONICAL_TARGETS, ConfirmedTargets
from stemlab.instrumentation.backend import DetectorScoreResult
from stemlab.instrumentation.clap_adapter import load_local_clap
from stemlab.instrumentation import verification


def _scores(offset: float = 0.0) -> dict[str, float]:
    return {
        target: offset + (len(CANONICAL_TARGETS) - index) / 100.0
        for index, target in enumerate(CANONICAL_TARGETS)
    }


def test_window_planning_is_deterministic_and_capped() -> None:
    assert plan_analysis_windows(8.0)[0].duration_seconds == 8.0
    assert [item.start_seconds for item in plan_analysis_windows(25.0)] == [0.0, 7.5, 15.0]
    long_a = plan_analysis_windows(1000.0)
    long_b = plan_analysis_windows(1000.0)
    assert long_a == long_b
    assert len(long_a) == MAX_WINDOWS == 8
    assert long_a[-1].start_seconds == 990.0


def test_taxonomy_and_aliases_are_closed_and_curated() -> None:
    assert tuple(PROMPT_ALIASES) == CANONICAL_TARGETS
    assert all(2 <= len(aliases) <= 4 for aliases in PROMPT_ALIASES.values())
    assert all(isinstance(alias, str) and alias for aliases in PROMPT_ALIASES.values() for alias in aliases)


def test_aggregation_is_deterministic_and_not_probability_shaped() -> None:
    windows = (_scores(0.0), _scores(0.01), _scores(-0.01))
    first = aggregate_instrument_evidence(windows)
    second = aggregate_instrument_evidence(windows)
    assert first == second
    assert first[0].target_id == "vocals"
    assert first[0].strong_window_hits == 3
    assert first[0].best_rank == 1
    assert first[0].state == "suggested"
    assert {item.state for item in first} <= {"suggested", "possible", "not_suggested"}


def test_manual_override_and_planning_collapse_core_to_one_pass() -> None:
    confirmed = ConfirmedTargets.from_iterable(
        ["piano", "vocals", "guitar", "bass", "drums", "strings", "synth_pad"]
    )
    plan = plan_for_targets(confirmed)
    assert len(plan.steps) == 1
    assert plan.steps[0].mode_id == "six-stems"
    assert plan.confirmed_targets[:5] == ("vocals", "drums", "bass", "guitar", "piano")
    unsupported = {item.target_id for item in plan.capabilities if item.status == "specialist_unavailable"}
    assert unsupported == {"synth_pad", "strings"}
    assert all(item.stem_role != "other" for item in plan.capabilities)
    assert plan_for_targets(ConfirmedTargets.from_iterable(["choir"])).steps == ()
    json.dumps(plan.to_dict())


class FakeDecoder:
    def duration_seconds(self, _path: Path) -> float:
        return 25.0

    def decode(self, _path: Path, window) -> np.ndarray:
        return np.full(480, window.index, dtype=np.float32)


class FakeDetector:
    model_id = "fake/clap"
    model_revision = "fixed"

    def score_windows(self, windows) -> DetectorScoreResult:
        return DetectorScoreResult(
            window_scores=tuple(_scores(index / 100.0) for index, _ in enumerate(windows)),
            effective_device="cuda",
            peak_cuda_allocated_bytes=123,
            peak_cuda_reserved_bytes=456,
        )

    def close(self) -> None:
        pass


def test_service_preserves_input_and_serializes_result(tmp_path: Path) -> None:
    source = tmp_path / "Música São João - João & Núbia.wav"
    source.write_bytes(b"read-only fixture")
    before = sha256_file(source)
    result = InstrumentationAnalysisService(FakeDetector(), FakeDecoder()).analyze(source)
    assert sha256_file(source) == before == result.input_sha256
    assert len(result.windows) == 3
    assert result.effective_device == "cuda"
    payload = result.to_dict()
    assert payload["input_path"] == str(source.resolve())
    assert len(payload["evidence"]) == len(CANONICAL_TARGETS)
    json.dumps(payload)


class FakeLoader:
    calls = []

    @classmethod
    def from_pretrained(cls, path, **kwargs):
        cls.calls.append((path, kwargs))
        return cls()


def test_clap_loader_is_local_only_and_disables_remote_code(tmp_path: Path) -> None:
    FakeLoader.calls = []
    load_local_clap(tmp_path, processor_cls=FakeLoader, model_cls=FakeLoader)
    assert len(FakeLoader.calls) == 2
    for path, kwargs in FakeLoader.calls:
        assert path == str(tmp_path.resolve())
        assert kwargs["local_files_only"] is True
        assert kwargs["trust_remote_code"] is False
    assert FakeLoader.calls[1][1]["weights_only"] is True
    assert FakeLoader.calls[1][1]["use_safetensors"] is False


def test_detector_verifier_rejects_receipt_and_artifact_tampering(
    tmp_path: Path, monkeypatch
) -> None:
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    config = model_dir / "config.json"
    weight = model_dir / "pytorch_model.bin"
    config.write_text('{"model_type":"clap","architectures":["ClapModel"]}', encoding="utf-8")
    weight.write_bytes(b"approved test weight")
    monkeypatch.setattr(verification, "REQUIRED_FILES", ("config.json", "pytorch_model.bin"))
    monkeypatch.setattr(verification, "EXPECTED_WEIGHT_SHA256", sha256_file(weight))
    files = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in (config, weight)
    }
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "source_repository": verification.EXPECTED_REPOSITORY,
                "source_revision": "wrong",
                "weight_expected_sha256": sha256_file(weight),
                "files": files,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="revision"):
        verification.verify_detector_artifacts(model_dir, receipt)
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["source_revision"] = verification.EXPECTED_REVISION
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    weight.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="size mismatch|SHA-256 mismatch"):
        verification.verify_detector_artifacts(model_dir, receipt)
