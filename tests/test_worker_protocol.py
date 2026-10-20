from __future__ import annotations

from pathlib import Path

import pytest

from stemlab.domain import DevicePolicy, OutputFormat
from stemlab.workers.protocol import (
    EVENT_PREFIX,
    JobLaunch,
    build_worker_command,
    encode_event,
    parse_event_line,
)
from stemlab.workers.analysis_protocol import AnalysisLaunch, build_analysis_worker_command


def test_worker_command_keeps_user_paths_as_arguments(tmp_path: Path) -> None:
    input_path = tmp_path / "Música São João - João & Núbia.wav"
    output_path = tmp_path / "á é í ó ú ã õ ç" / "Ana-Nóbrega"
    program, arguments = build_worker_command(
        tmp_path,
        JobLaunch(
            input_path,
            "six-stems",
            output_path,
            OutputFormat.FLAC,
            DevicePolicy.CPU_REQUIRED,
            ("bass", "guitar"),
        ),
    )
    assert program == str(tmp_path.resolve() / ".venv" / "Scripts" / "python.exe")
    assert arguments[:5] == ["-X", "utf8", "-m", "stemlab.workers.run_job", "--input"]
    assert str(input_path.resolve()) in arguments
    assert str(output_path.resolve()) in arguments
    assert "flac" in arguments
    assert arguments[arguments.index("--device") + 1] == "cpu"
    assert [arguments[index + 1] for index, item in enumerate(arguments) if item == "--stem"] == [
        "bass",
        "guitar",
    ]
    assert all("shell=True" not in argument for argument in arguments)


def test_worker_command_serializes_mp3_output(tmp_path: Path) -> None:
    _, arguments = build_worker_command(
        tmp_path,
        JobLaunch(
            tmp_path / "entrada.mp3",
            "six-stems",
            tmp_path / "out",
            OutputFormat.MP3,
        ),
    )
    assert arguments[arguments.index("--format") + 1] == "mp3"


def test_worker_event_round_trip_and_log_filtering() -> None:
    unicode_path = "C:/á é í ó ú ã õ ç/Música São João - João & Núbia/Ana-Nóbrega.wav"
    encoded = encode_event("completed", message="concluído: Música São João", payload={"output_dir": unicode_path})
    assert encoded.startswith(EVENT_PREFIX)
    assert "Nóbrega" in encoded
    assert "�" not in encoded
    assert parse_event_line(encoded) == {
        "protocol_version": 2,
        "type": "completed",
        "message": "concluído: Música São João",
        "payload": {"output_dir": unicode_path},
    }
    assert parse_event_line("ordinary backend log") is None


def test_worker_event_rejects_unknown_protocol() -> None:
    with pytest.raises(ValueError, match="protocol version"):
        parse_event_line(
            'STEMLAB_EVENT {"protocol_version":1,"type":"status","message":"x","payload":{}}'
        )


@pytest.mark.parametrize(
    "roles, message",
    [
        ((), "at least one"),
        (("bass", "bass"), "unique"),
        (("../song.wav",), "unsupported"),
    ],
)
def test_job_launch_rejects_invalid_core_selection(
    tmp_path: Path, roles: tuple[str, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        JobLaunch(
            tmp_path / "input.wav",
            "six-stems",
            tmp_path / "out",
            OutputFormat.WAV,
            requested_roles=roles,
        )


def test_analysis_worker_command_preserves_unicode_and_uses_utf8(tmp_path: Path) -> None:
    input_path = tmp_path / "á é í ó ú ã õ ç" / "Ana-Nóbrega.wav"
    program, arguments = build_analysis_worker_command(tmp_path, AnalysisLaunch(input_path))
    assert program == str(tmp_path.resolve() / ".venv" / "Scripts" / "python.exe")
    assert arguments[:5] == ["-X", "utf8", "-m", "stemlab.workers.run_analysis", "--input"]
    assert arguments[-1] == str(input_path.resolve())
