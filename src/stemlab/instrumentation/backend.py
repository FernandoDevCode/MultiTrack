from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np


@dataclass(frozen=True)
class DetectorScoreResult:
    window_scores: tuple[dict[str, float], ...]
    effective_device: str
    peak_cuda_allocated_bytes: int
    peak_cuda_reserved_bytes: int


class InstrumentDetector(Protocol):
    def score_windows(self, windows: Sequence[np.ndarray]) -> DetectorScoreResult: ...

    def close(self) -> None: ...
