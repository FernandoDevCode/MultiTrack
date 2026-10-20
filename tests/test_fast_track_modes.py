from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from stemlab.app import (
    CORE_STEMS,
    MODES,
    SIX_STEMS,
    VOCALS_HQ,
    build_request,
    get_mode,
    new_output_dir,
)
from stemlab.domain import DevicePolicy, OutputFormat


def test_fast_track_exposes_only_two_curated_modes() -> None:
    assert [mode.label for mode in MODES] == [
        "Vocals HQ (experimental)",
        "Core Stems",
    ]
    assert VOCALS_HQ.expected_roles == ("instrumental", "vocals")
    assert SIX_STEMS.expected_roles == (
        "vocals",
        "drums",
        "bass",
        "guitar",
        "piano",
        "other",
    )
    assert "experimental" in VOCALS_HQ.description.lower()
    assert "not redistributable" in VOCALS_HQ.description


def test_core_stems_plan_is_plain_data_and_resolves_to_existing_mode() -> None:
    assert CORE_STEMS.to_dict() == {
        "pipeline_id": "core-stems",
        "label": "Core Stems",
        "description": "BS-RoFormer SW: vocals, drums, bass, guitar, piano e other.",
        "steps": ({"mode_id": "six-stems"},),
        "confirmed_targets": (),
        "capabilities": (),
    }
    assert CORE_STEMS.steps[0].mode_id == SIX_STEMS.mode_id


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown separation mode"):
        get_mode("arbitrary-checkpoint")


def test_six_stem_request_uses_verified_local_artifacts(tmp_path: Path) -> None:
    request = build_request(
        repo_root=tmp_path,
        input_path=tmp_path / "song.wav",
        mode_id=SIX_STEMS.mode_id,
        output_dir=tmp_path / "outputs" / "song" / "run",
        output_format=OutputFormat.FLAC,
    )
    assert request.device_policy is DevicePolicy.AUTO
    assert request.output_format is OutputFormat.FLAC
    assert request.model.backend_filename is None
    assert request.model.checkpoint_path == tmp_path / "models" / "BS-Roformer-SW.ckpt"
    assert request.model.expected_sha256 == "24e7d35ee9c64415673d3fd33e06a67cac2c103c5df6267ba1576459c775916e"
    assert request.model.config_paths == (tmp_path / "models" / "BS-Roformer-SW.yaml",)
    assert request.model.expected_config_sha256 == (
        "b558996f1e25eb48798bd6502505a5de94c4f966d6edfb1a0420f06cc40b501a",
    )
    assert request.expected_roles == SIX_STEMS.expected_roles
    assert request.requested_roles is None


@pytest.mark.parametrize("policy", tuple(DevicePolicy))
def test_request_propagates_every_device_policy(tmp_path: Path, policy: DevicePolicy) -> None:
    request = build_request(
        repo_root=tmp_path,
        input_path=tmp_path / "song.wav",
        mode_id=SIX_STEMS.mode_id,
        output_dir=tmp_path / "out",
        output_format=OutputFormat.WAV,
        device_policy=policy,
        requested_roles=("bass", "guitar"),
    )
    assert request.device_policy is policy
    assert request.requested_roles == ("bass", "guitar")
    assert request.use_autocast is (policy is not DevicePolicy.CPU_REQUIRED)


def test_output_directory_is_safe_unique_and_below_outputs(tmp_path: Path) -> None:
    output = new_output_dir(
        tmp_path,
        Path("C:/Music/Minha Música & Solo.wav"),
        now=datetime(2026, 9, 29, 18, 20, 30, 123456, tzinfo=timezone.utc),
    )
    assert output == (
        tmp_path.resolve()
        / "outputs"
        / "minha-musica-solo"
        / "20260929-182030-123456"
    )
