"""Observe completed iterations without changing model work or audio samples."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sized
import time
from typing import TypeVar

from stemlab.domain.progress import ProgressCallback, SeparationProgress

T = TypeVar("T")


def observe_iterations(
    iterable: Iterable[T],
    *,
    total: int,
    callback: ProgressCallback,
    clock: Callable[[], float] = time.perf_counter,
) -> Iterator[T]:
    started = clock()
    callback(SeparationProgress("inference", total=total))
    for completed, item in enumerate(iterable, 1):
        yield item
        # Resuming after yield means the caller finished this chunk. A failed
        # chunk must never be counted as completed.
        elapsed = max(0.0, clock() - started)
        eta = elapsed / completed * (total - completed)
        callback(SeparationProgress("inference", completed, total, eta))


def iteration_total(iterable, explicit_total=None) -> int | None:
    total = explicit_total
    if total is None and isinstance(iterable, Sized):
        total = len(iterable)
    return total if type(total) is int and total > 0 else None
