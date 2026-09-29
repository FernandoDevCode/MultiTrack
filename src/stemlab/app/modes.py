from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import unicodedata

from stemlab.domain import (
    DevicePolicy,
    ModelSpec,
    OutputFormat,
    SeparationRequest,
)


@dataclass(frozen=True)
class ModeDefinition:
    mode_id: str
    label: str
    description: str
    model_id: str
    checkpoint_filename: str
    checkpoint_sha256: str
    config_files: tuple[tuple[str, str], ...]
    expected_roles: tuple[str, ...]
    backend_filename: str | None = None

    def model_spec(self, repo_root: Path) -> ModelSpec:
        model_root = repo_root.resolve() / "models"
        return ModelSpec(
            model_id=self.model_id,
            checkpoint_path=model_root / self.checkpoint_filename,
            expected_sha256=self.checkpoint_sha256,
            config_paths=tuple(model_root / name for name, _ in self.config_files),
            expected_config_sha256=tuple(sha256 for _, sha256 in self.config_files),
            backend_filename=self.backend_filename,
        )


VOCALS_HQ = ModeDefinition(
    mode_id="vocals-hq-experimental",
    label="Vocals HQ (experimental)",
    description=(
        "BS-RoFormer local experimental. The checkpoint license is unknown and "
        "the weight is not redistributable by the current project decision."
    ),
    model_id="bs-roformer-viperx-1297-experimental-smoke",
    checkpoint_filename="model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    checkpoint_sha256="5b84f37e8d444c8cb30c79d77f613a41c05868ff9c9ac6c7049c00aefae115aa",
    config_files=(
        (
            "model_bs_roformer_ep_317_sdr_12.9755.yaml",
            "2bfdd16c656bd9519aba757cc4f8834b7ede675eb1e00ec4772d74ae1c41af7f",
        ),
    ),
    expected_roles=("instrumental", "vocals"),
)

SIX_STEMS = ModeDefinition(
    mode_id="six-stems-baseline",
    label="6 Stems (baseline)",
    description="htdemucs_6s baseline: vocals, drums, bass, guitar, piano and other.",
    model_id="htdemucs-6s-baseline",
    checkpoint_filename="5c90dfd2-34c22ccb.th",
    checkpoint_sha256="34c22ccb381c6f9fdbf324f04e1e2fe21aaaf293f5ded163a162697ff9a02ddd",
    config_files=(
        (
            "htdemucs_6s.yaml",
            "207405151270af8fd81c2373c25d27950916682ac91dca7884a11ce13dad6f58",
        ),
    ),
    expected_roles=("vocals", "drums", "bass", "guitar", "piano", "other"),
    backend_filename="htdemucs_6s.yaml",
)

MODES = (VOCALS_HQ, SIX_STEMS)
_MODES_BY_ID = {mode.mode_id: mode for mode in MODES}


def get_mode(mode_id: str) -> ModeDefinition:
    try:
        return _MODES_BY_ID[mode_id]
    except KeyError as exc:
        raise ValueError(f"Unknown separation mode: {mode_id}") from exc


def build_request(
    *,
    repo_root: Path,
    input_path: Path,
    mode_id: str,
    output_dir: Path,
    output_format: OutputFormat,
) -> SeparationRequest:
    mode = get_mode(mode_id)
    return SeparationRequest(
        input_path=input_path,
        model=mode.model_spec(repo_root),
        output_dir=output_dir,
        output_format=output_format,
        device_policy=DevicePolicy.CUDA_REQUIRED,
        use_autocast=True,
        expected_roles=mode.expected_roles,
    )


def new_output_dir(repo_root: Path, input_path: Path, *, now: datetime | None = None) -> Path:
    timestamp = now or datetime.now(timezone.utc)
    run_id = timestamp.strftime("%Y%m%d-%H%M%S-%f")
    return repo_root.resolve() / "outputs" / _track_slug(input_path.stem) / run_id


def _track_slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug[:80] or "track"
