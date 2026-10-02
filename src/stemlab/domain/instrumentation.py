from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


CANONICAL_TARGETS = (
    "vocals",
    "drums",
    "bass",
    "guitar",
    "piano",
    "keys",
    "synth_pad",
    "organ",
    "percussion",
    "strings",
    "brass",
    "woodwind",
    "choir",
)
_TARGET_SET = frozenset(CANONICAL_TARGETS)


@dataclass(frozen=True)
class AnalysisWindow:
    index: int
    start_seconds: float
    duration_seconds: float


@dataclass(frozen=True)
class InstrumentEvidence:
    target_id: str
    aggregate_similarity: float
    peak_similarity: float
    strong_window_hits: int
    best_rank: int
    state: str
    window_scores: tuple[float, ...]
    window_ranks: tuple[int, ...]


@dataclass(frozen=True)
class InstrumentationAnalysisResult:
    schema_version: int
    input_path: Path
    input_sha256: str
    duration_seconds: float
    windows: tuple[AnalysisWindow, ...]
    evidence: tuple[InstrumentEvidence, ...]
    model_id: str
    model_revision: str
    effective_device: str
    runtime_seconds: float
    peak_cuda_allocated_bytes: int
    peak_cuda_reserved_bytes: int

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["input_path"] = str(self.input_path)
        return value


@dataclass(frozen=True)
class ConfirmedTargets:
    target_ids: tuple[str, ...]

    @classmethod
    def from_iterable(cls, target_ids: Iterable[str]) -> ConfirmedTargets:
        selected = set(target_ids)
        unknown = selected - _TARGET_SET
        if unknown:
            raise ValueError(f"Unknown instrumentation targets: {sorted(unknown)}")
        return cls(tuple(target for target in CANONICAL_TARGETS if target in selected))

    def to_dict(self) -> dict[str, list[str]]:
        return {"target_ids": list(self.target_ids)}


@dataclass(frozen=True)
class TargetCapability:
    target_id: str
    status: str
    pipeline_id: str | None
    stem_role: str | None

    def __post_init__(self) -> None:
        if self.target_id not in _TARGET_SET:
            raise ValueError(f"Unknown instrumentation target: {self.target_id}")
        if self.status not in {"core_available", "specialist_unavailable"}:
            raise ValueError(f"Unknown capability status: {self.status}")
