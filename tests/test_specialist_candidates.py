from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from stemlab.domain import BackendSeparationError, ModelIntegrityError
from stemlab.separation import specialist_candidates as registry
from stemlab.separation.audio_separator_adapter import (
    AudioSeparatorBackend,
    _VerifiedLocalSpecialistSeparator,
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_specialist_registry_contains_only_checkpoint3_allowlist() -> None:
    assert {item.candidate_id for item in registry.SPECIALIST_CANDIDATES} == {
        "lead_rhythm_listra92",
        "bass_xlancer",
    }
    assert registry.LEAD_RHYTHM_LISTRA92.config_sha256 == (
        "fc47975bba58b7b4c6de363bfe158943092c77bfb0b9a41c0c741eafba330359"
    )
    assert registry.BASS_XLANCER.config_sha256 == (
        "dd9164936be88e636ccae0b6689e5b2f299f2cd9668918071e0795cd8cdd7e00"
    )


def test_unknown_candidate_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown specialist candidate"):
        registry.build_specialist_model_spec("arbitrary_model", Path("models"))


def test_allowlisted_id_cannot_be_redirected_to_arbitrary_path(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    spec = registry.build_specialist_model_spec(
        registry.LEAD_RHYTHM_LISTRA92.candidate_id, models_dir
    )
    redirected = replace(spec, checkpoint_path=tmp_path / "arbitrary.ckpt")

    with pytest.raises(BackendSeparationError, match="internal allowlist"):
        registry.resolve_verified_specialist(redirected, models_dir)


@pytest.mark.parametrize("mismatch", ["checkpoint", "config"])
def test_checkpoint_and_config_hash_mismatches_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    checkpoint_bytes = b"checkpoint"
    config_bytes = b"config"
    candidate = replace(
        registry.LEAD_RHYTHM_LISTRA92,
        checkpoint_relative_path=Path("experimental/test/model.ckpt"),
        checkpoint_bytes=len(checkpoint_bytes),
        checkpoint_sha256=(
            "0" * 64 if mismatch == "checkpoint" else _sha256(checkpoint_bytes)
        ),
        config_relative_path=Path("experimental/test/model.yaml"),
        config_bytes=len(config_bytes),
        config_sha256=("0" * 64 if mismatch == "config" else _sha256(config_bytes)),
    )
    monkeypatch.setattr(registry, "_BY_ID", {candidate.candidate_id: candidate})
    models_dir = tmp_path / "models"
    checkpoint = models_dir / candidate.checkpoint_relative_path
    config = models_dir / candidate.config_relative_path
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(checkpoint_bytes)
    config.write_bytes(config_bytes)

    with pytest.raises(ModelIntegrityError, match="SHA-256 mismatch"):
        registry.resolve_verified_specialist(candidate.model_spec(models_dir), models_dir)


def test_local_specialist_resolver_uses_no_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_network(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr("requests.get", fail_network)
    resolver = object.__new__(_VerifiedLocalSpecialistSeparator)
    resolver._stemlab_specialist = registry.LEAD_RHYTHM_LISTRA92
    resolver.model_file_dir = str(tmp_path / "models")

    resolved = resolver.download_model_files(
        registry.LEAD_RHYTHM_LISTRA92.checkpoint_relative_path.name
    )

    assert resolved[0] == "mbr_lead_rhythm_guitar_listra92.ckpt"
    assert resolved[1] == "MDXC"
    assert resolved[4].endswith("mbr_lead_rhythm_guitar_listra92_config.yaml")


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("song_(Lead)_model.wav", "lead"),
        ("song_(Rhythm)_model.wav", "rhythm"),
        ("song_(bass)_model.wav", "bass"),
        ("song_(other)_model.wav", "other"),
    ],
)
def test_specialist_roles_are_parsed_case_insensitively(
    filename: str, expected: str
) -> None:
    assert AudioSeparatorBackend._role_for(Path(filename)) == expected


def test_local_resolver_rejects_a_different_filename(tmp_path: Path) -> None:
    resolver = object.__new__(_VerifiedLocalSpecialistSeparator)
    resolver._stemlab_specialist = registry.BASS_XLANCER
    resolver.model_file_dir = str(tmp_path / "models")

    with pytest.raises(ValueError, match="not allowlisted"):
        resolver.download_model_files("arbitrary.ckpt")
