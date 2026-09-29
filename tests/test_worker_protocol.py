from __future__ import annotations

from pathlib import Path

import pytest

from stemlab.domain import OutputFormat
from stemlab.workers.protocol import (
    EVENT_PREFIX,
    JobLaunch,
    build_worker_command,
    encode_event,
    parse_event_line,
)


def test_worker_command_keeps_user_paths_as_arguments(tmp_path: Path) -> None:
    input_path = tmp_path / "song & echo unsafe.wav"
    output_path = tmp_path / "outputs" / "run & keep"
    program, arguments = build_worker_command(
        tmp_path,
        JobLaunch(input_path, "six-stems-baseline", output_path, OutputFormat.FLAC),
    )
    assert program == str(tmp_path.resolve() / ".venv" / "Scripts" / "python.exe")
    assert arguments[:3] == ["-m", "stemlab.workers.run_job", "--input"]
    assert str(input_path.resolve()) in arguments
    assert str(output_path.resolve()) in arguments
    assert "flac" in arguments
    assert all("shell=True" not in argument for argument in arguments)


def test_worker_event_round_trip_and_log_filtering() -> None:
    encoded = encode_event("completed", message="done", payload={"output_dir": "x"})
    assert encoded.startswith(EVENT_PREFIX)
    assert parse_event_line(encoded) == {
        "protocol_version": 1,
        "type": "completed",
        "message": "done",
        "payload": {"output_dir": "x"},
    }
    assert parse_event_line("ordinary backend log") is None


def test_worker_event_rejects_unknown_protocol() -> None:
    with pytest.raises(ValueError, match="protocol version"):
        parse_event_line(
            'STEMLAB_EVENT {"protocol_version":2,"type":"status","message":"x","payload":{}}'
        )
