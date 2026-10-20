from __future__ import annotations

from pathlib import Path

import pytest

from stemlab.domain.progress import SeparationProgress
from stemlab.separation.progress import observe_iterations
from stemlab.workers.protocol import encode_event, parse_event_line


def test_eta_uses_completed_work_and_observed_time() -> None:
    now = [100.0]
    events = []
    work = observe_iterations(
        ["a", "b", "c", "d"], total=4,
        callback=events.append, clock=lambda: now[0],
    )
    assert next(work) == "a"
    assert events[-1].completed == 0
    assert events[-1].eta_seconds is None
    now[0] += 10
    assert next(work) == "b"
    assert events[-1].completed == 1
    assert events[-1].eta_seconds == 30
    now[0] += 10
    assert next(work) == "c"
    assert events[-1].percent == 50
    assert events[-1].eta_seconds == 20
    now[0] += 5
    assert next(work) == "d"
    assert events[-1].eta_seconds == pytest.approx(25 / 3)
    now[0] += 5
    with pytest.raises(StopIteration):
        next(work)
    assert events[-1].percent == 99
    assert events[-1].eta_seconds == 0


def test_adapter_restores_hook_and_does_not_count_failed_chunk(tmp_path: Path) -> None:
    from audio_separator.separator.architectures import mdxc_separator
    from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend

    events = []
    backend = AudioSeparatorBackend(models_dir=tmp_path, on_progress=events.append)
    original = mdxc_separator.tqdm
    processed = []
    with pytest.raises(RuntimeError, match="chunk failed"):
        with backend._observe_inference_progress("cpu"):
            for item in mdxc_separator.tqdm([1, 2, 3], disable=True):
                if item == 2:
                    raise RuntimeError("chunk failed")
                processed.append(item)
    assert mdxc_separator.tqdm is original
    assert processed == [1]
    assert max(event.completed for event in events) == 1
    assert not any(event.phase == "writing" for event in events)

    events.clear()
    with backend._observe_inference_progress("cpu"):
        assert list(mdxc_separator.tqdm([1, 2, 3], disable=True)) == [1, 2, 3]
    assert mdxc_separator.tqdm is original
    assert events[-1].phase == "writing"
    assert events[-2].completed == 3


def test_unknown_iteration_total_does_not_invent_progress(tmp_path: Path) -> None:
    from audio_separator.separator.architectures import mdxc_separator
    from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend

    events = []
    backend = AudioSeparatorBackend(models_dir=tmp_path, on_progress=events.append)
    with backend._observe_inference_progress("cpu"):
        assert list(mdxc_separator.tqdm(iter([1, 2]), disable=True)) == [1, 2]
    assert not events


def test_progress_event_round_trip() -> None:
    observation = SeparationProgress("inference", 3, 10, 12.5)
    event = parse_event_line(encode_event("progress", message="", payload=observation.to_dict()))
    assert event is not None
    assert SeparationProgress(**event["payload"]) == observation


@pytest.mark.parametrize("payload", [
    {"phase": "inference", "completed": 1, "total": 0},
    {"phase": "inference", "completed": -1, "total": 10},
    {"phase": "inference", "completed": 11, "total": 10},
    {"phase": "inference", "completed": True, "total": 10},
    {"phase": "inference", "completed": 1, "total": 10, "eta_seconds": float("nan")},
    {"phase": "inference", "completed": 1, "total": 10, "eta_seconds": float("inf")},
    {"phase": "inference", "completed": 1, "total": 10, "eta_seconds": -1},
    {"phase": "writing", "eta_seconds": 12},
    {"phase": "unknown"},
])
def test_progress_protocol_rejects_invalid_observations(payload: dict) -> None:
    with pytest.raises((ValueError, TypeError)):
        parse_event_line(encode_event("progress", message="", payload=payload))
