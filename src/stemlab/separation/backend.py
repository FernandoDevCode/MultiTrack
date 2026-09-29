from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from stemlab.domain import AudioMetadata, SeparationRequest


@dataclass(frozen=True)
class BackendStem:
    role: str
    path: Path


@dataclass(frozen=True)
class BackendResult:
    backend_id: str
    effective_device: str
    effective_precision: str | None
    model_load_seconds: float
    inference_seconds: float
    total_seconds: float
    stems: tuple[BackendStem, ...]
    peak_cuda_allocated_bytes: int | None = None
    peak_cuda_reserved_bytes: int | None = None
    warnings: tuple[str, ...] = ()


class SeparationBackend(Protocol):
    def separate(
        self, request: SeparationRequest, input_metadata: AudioMetadata
    ) -> BackendResult: ...
