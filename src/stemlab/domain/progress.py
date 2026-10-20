"""Serializable progress observations, independent of the UI and model runtime."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Callable


@dataclass(frozen=True)
class SeparationProgress:
    phase: str
    completed: int = 0
    total: int = 0
    eta_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.phase not in {"preparing", "loading", "inference", "writing", "validating"}:
            raise ValueError("Unknown separation progress phase")
        if (
            type(self.completed) is not int or type(self.total) is not int
            or not 0 <= self.completed <= self.total
        ):
            raise ValueError("Invalid progress counters")
        if self.phase == "inference" and self.total == 0:
            raise ValueError("Inference progress requires a positive total")
        if self.eta_seconds is not None and (
            type(self.eta_seconds) not in (int, float)
            or not math.isfinite(self.eta_seconds) or self.eta_seconds < 0
            or self.phase != "inference" or self.completed == 0
        ):
            raise ValueError("Invalid inference ETA")

    @property
    def percent(self) -> int:
        # The chunk fraction measures inference, not file publication. Reserve
        # 100% for the worker's successful terminal event after validation.
        if self.phase in {"writing", "validating"}:
            return 99
        return min(99, self.completed * 100 // self.total) if self.total else 0

    def to_dict(self) -> dict:
        return asdict(self)


ProgressCallback = Callable[[SeparationProgress], None]
