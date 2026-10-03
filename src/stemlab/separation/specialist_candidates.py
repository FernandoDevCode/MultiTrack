from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from stemlab.domain import (
    BackendSeparationError,
    ModelIntegrityError,
    ModelMissingError,
    ModelSpec,
)


@dataclass(frozen=True)
class SpecialistCandidate:
    candidate_id: str
    display_name: str
    task: str
    checkpoint_relative_path: Path
    checkpoint_bytes: int
    checkpoint_sha256: str
    config_relative_path: Path
    config_bytes: int
    config_sha256: str
    expected_roles: tuple[str, ...]
    source_repo: str
    source_revision: str
    license: str = "unknown"
    redistribution: str = "research-only"

    def model_spec(self, models_dir: Path) -> ModelSpec:
        root = models_dir.resolve()
        return ModelSpec(
            model_id=self.candidate_id,
            checkpoint_path=root / self.checkpoint_relative_path,
            expected_sha256=self.checkpoint_sha256,
            config_paths=(root / self.config_relative_path,),
            expected_config_sha256=(self.config_sha256,),
            backend_filename=self.checkpoint_relative_path.name,
        )


LEAD_RHYTHM_LISTRA92 = SpecialistCandidate(
    candidate_id="lead_rhythm_listra92",
    display_name="Mel-Band Roformer Lead/Rhythm Guitar by listra92",
    task="lead_rhythm",
    checkpoint_relative_path=Path(
        "experimental/lead_rhythm_listra92/mbr_lead_rhythm_guitar_listra92.ckpt"
    ),
    checkpoint_bytes=337_073_664,
    checkpoint_sha256="b3c47bca33609ca1ba0bb2d2076410bfd1eb941b051b72afc1f3e24d12b17eef",
    config_relative_path=Path(
        "experimental/lead_rhythm_listra92/mbr_lead_rhythm_guitar_listra92_config.yaml"
    ),
    config_bytes=2_673,
    config_sha256="fc47975bba58b7b4c6de363bfe158943092c77bfb0b9a41c0c741eafba330359",
    expected_roles=("lead", "rhythm"),
    source_repo="noblebarkrr/mvsepless_resources",
    source_revision="2749bf2dcd4d04f019c0581c49cb8891d77fddb4",
)

BASS_XLANCER = SpecialistCandidate(
    candidate_id="bass_xlancer",
    display_name="BS Roformer Bass by Xlance",
    task="bass",
    checkpoint_relative_path=Path(
        "experimental/bass_xlancer/bs_bass_xlancer.ckpt"
    ),
    checkpoint_bytes=204_411_168,
    checkpoint_sha256="c409465e3dccfd83fa34e6a807dbdae2f4f1db24f2f85a0fdc146b6fa828afff",
    config_relative_path=Path(
        "experimental/bass_xlancer/bs_bass_xlancer_config.yaml"
    ),
    config_bytes=1_719,
    config_sha256="dd9164936be88e636ccae0b6689e5b2f299f2cd9668918071e0795cd8cdd7e00",
    expected_roles=("bass", "other"),
    source_repo="noblebarkrr/mvsepless_resources",
    source_revision="4e97e0fec0e787df4573cd8cb68a5a8d216dc120",
)

SPECIALIST_CANDIDATES = (LEAD_RHYTHM_LISTRA92, BASS_XLANCER)
_BY_ID = {candidate.candidate_id: candidate for candidate in SPECIALIST_CANDIDATES}


def get_specialist_candidate(candidate_id: str) -> SpecialistCandidate:
    try:
        return _BY_ID[candidate_id]
    except KeyError as exc:
        raise ValueError(f"Unknown specialist candidate: {candidate_id}") from exc


def build_specialist_model_spec(candidate_id: str, models_dir: Path) -> ModelSpec:
    """Build a spec from the allowlist; callers cannot supply artifact paths."""
    return get_specialist_candidate(candidate_id).model_spec(models_dir)


def resolve_verified_specialist(
    model: ModelSpec, models_dir: Path
) -> SpecialistCandidate | None:
    """Validate an allowlisted specialist tuple and its bytes before model load."""
    candidate = _BY_ID.get(model.model_id)
    if candidate is None:
        return None

    expected = candidate.model_spec(models_dir)
    observed_tuple = (
        model.checkpoint_path.resolve(),
        model.expected_sha256.lower(),
        tuple(path.resolve() for path in model.config_paths),
        tuple(value.lower() for value in model.expected_config_sha256),
        model.backend_filename,
    )
    expected_tuple = (
        expected.checkpoint_path.resolve(),
        expected.expected_sha256.lower(),
        tuple(path.resolve() for path in expected.config_paths),
        tuple(value.lower() for value in expected.expected_config_sha256),
        expected.backend_filename,
    )
    if observed_tuple != expected_tuple:
        raise BackendSeparationError(
            "Specialist model tuple does not match the internal allowlist.",
            details={"candidate_id": model.model_id},
        )

    _verify_file(
        expected.checkpoint_path,
        expected_bytes=candidate.checkpoint_bytes,
        expected_sha256=candidate.checkpoint_sha256,
    )
    _verify_file(
        expected.config_paths[0],
        expected_bytes=candidate.config_bytes,
        expected_sha256=candidate.config_sha256,
    )
    return candidate


def verify_all_specialist_candidates(models_dir: Path) -> tuple[SpecialistCandidate, ...]:
    for candidate in SPECIALIST_CANDIDATES:
        resolve_verified_specialist(candidate.model_spec(models_dir), models_dir)
    return SPECIALIST_CANDIDATES


def _verify_file(path: Path, *, expected_bytes: int, expected_sha256: str) -> None:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ModelMissingError(
            f"Specialist artifact does not exist: {resolved}",
            details={"path": str(resolved)},
        )
    actual_bytes = resolved.stat().st_size
    if actual_bytes != expected_bytes:
        raise ModelIntegrityError(
            "Specialist artifact size mismatch.",
            details={
                "path": str(resolved),
                "expected_bytes": expected_bytes,
                "actual_bytes": actual_bytes,
            },
        )
    actual_sha256 = _sha256_file(resolved)
    if actual_sha256 != expected_sha256:
        raise ModelIntegrityError(
            "Specialist artifact SHA-256 mismatch.",
            details={
                "path": str(resolved),
                "expected": expected_sha256,
                "actual": actual_sha256,
            },
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
