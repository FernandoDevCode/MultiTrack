from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
import re
from typing import Any


_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class OutputFormat(str, Enum):
    WAV = "WAV"
    FLAC = "FLAC"


class DevicePolicy(str, Enum):
    CUDA_REQUIRED = "cuda"
    AUTO = "auto"


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    checkpoint_path: Path
    expected_sha256: str
    config_paths: tuple[Path, ...] = ()
    expected_config_sha256: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id must not be empty")
        if not _SHA256_RE.fullmatch(self.expected_sha256):
            raise ValueError("expected_sha256 must contain exactly 64 hexadecimal characters")
        if len(self.config_paths) != len(self.expected_config_sha256):
            raise ValueError("each config path must have one expected SHA-256")
        if any(not _SHA256_RE.fullmatch(item) for item in self.expected_config_sha256):
            raise ValueError("config SHA-256 values must contain exactly 64 hexadecimal characters")


@dataclass(frozen=True)
class SeparationRequest:
    input_path: Path
    model: ModelSpec
    output_dir: Path
    output_format: OutputFormat = OutputFormat.WAV
    device_policy: DevicePolicy = DevicePolicy.CUDA_REQUIRED
    use_autocast: bool = True


@dataclass(frozen=True)
class AudioMetadata:
    path: Path
    format: str
    subtype: str
    frames: int
    duration_seconds: float
    sample_rate: int
    channels: int
    bytes: int
    sha256: str


@dataclass(frozen=True)
class FileArtifact:
    path: Path
    bytes: int
    sha256: str


@dataclass(frozen=True)
class ModelArtifact:
    model_id: str
    checkpoint: FileArtifact
    configs: tuple[FileArtifact, ...]


@dataclass(frozen=True)
class StemArtifact:
    role: str
    path: Path
    format: str
    duration_seconds: float
    sample_rate: int
    channels: int
    bytes: int
    sha256: str
    rms: float
    peak: float


@dataclass(frozen=True)
class TimingInfo:
    model_load_seconds: float
    inference_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class DeviceInfo:
    requested_policy: DevicePolicy
    effective_device: str
    effective_precision: str | None
    peak_cuda_allocated_bytes: int | None = None
    peak_cuda_reserved_bytes: int | None = None


@dataclass(frozen=True)
class SeparationErrorInfo:
    code: str
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class SeparationResult:
    schema_version: int
    success: bool
    started_at: str
    completed_at: str
    input: AudioMetadata | None
    model: ModelArtifact | None
    backend: str | None
    device: DeviceInfo | None
    timings: TimingInfo | None
    stems: tuple[StemArtifact, ...]
    warnings: tuple[str, ...]
    error: SeparationErrorInfo | None
    manifest_path: Path | None

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value
