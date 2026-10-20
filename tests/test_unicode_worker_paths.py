from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
import pytest
import soundfile as sf

from stemlab.audio import MultiStemPlayer
from stemlab.domain import DevicePolicy, OutputFormat
from stemlab.domain.progress import SeparationProgress
from stemlab.workers.protocol import JobLaunch, encode_event
from stemlab.workers.qprocess_job import QProcessJob


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_qprocess_worker_payload_preserves_unicode_path_and_player_opens_it(
    tmp_path: Path, qt_app, monkeypatch
) -> None:
    unicode_dir = tmp_path / "á é í ó ú ã õ ç" / "Música São João - João & Núbia"
    unicode_dir.mkdir(parents=True)
    stem_path = unicode_dir / "Ana-Nóbrega.wav"
    sf.write(stem_path, np.zeros((256, 2), dtype=np.float32), 44_100, subtype="FLOAT")
    expected_path = str(stem_path.resolve())
    child = (
        "import json, sys; "
        "path = sys.argv[1]; "
        "event = {'protocol_version': 2, 'type': 'completed', 'message': 'concluído', "
        "'payload': {'output_dir': path, 'result': {'stems': [{'role': 'vocals', 'path': path}]}}}; "
        "sys.stdout.buffer.write(('STEMLAB_EVENT ' + json.dumps(event, ensure_ascii=False) + '\\n').encode('utf-8')); "
        "sys.stdout.flush()"
    )
    monkeypatch.setattr(
        "stemlab.workers.qprocess_job.build_worker_command",
        lambda _root, _job: (sys.executable, ["-X", "utf8", "-c", child, expected_path]),
    )
    job = QProcessJob(tmp_path)
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "-1")
    environment = job._project_environment()
    assert environment.value("PYTHONUTF8") == "1"
    assert environment.value("PYTHONIOENCODING") == "utf-8:strict"
    assert environment.value("HF_HUB_OFFLINE") == "1"
    assert environment.value("TRANSFORMERS_OFFLINE") == "1"
    assert environment.value("CUDA_VISIBLE_DEVICES") == "-1"
    cpu_environment = job._project_environment(
        JobLaunch(
            stem_path,
            "six-stems",
            unicode_dir,
            OutputFormat.WAV,
            device_policy=DevicePolicy.CPU_REQUIRED,
        )
    )
    assert cpu_environment.value("CUDA_VISIBLE_DEVICES") == "-1"
    payloads: list[dict] = []
    failures: list[str] = []
    loop = QEventLoop()
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    job.completed.connect(lambda payload: (payloads.append(payload), loop.quit()))
    job.failed.connect(lambda message: (failures.append(message), loop.quit()))
    timeout.start(5_000)
    job.start(JobLaunch(stem_path, "six-stems", unicode_dir, OutputFormat.WAV))
    loop.exec()
    timeout.stop()

    assert not failures
    assert payloads
    received_path = payloads[0]["result"]["stems"][0]["path"]
    assert received_path == expected_path
    assert "�" not in received_path
    player = MultiStemPlayer()
    player.load_session({"vocals": Path(received_path)})
    assert player.roles == ("vocals",)
    assert player.state().total_frames == 256
    player.close()


def test_invalid_utf8_in_structured_event_is_explicit_recoverable_error(
    tmp_path: Path, qt_app
) -> None:
    job = QProcessJob(tmp_path)
    failures: list[str] = []
    completions: list[dict] = []
    job.failed.connect(failures.append)
    job.completed.connect(completions.append)
    job._handle_stdout_line(b'STEMLAB_EVENT {"protocol_version":2,"type":"status","message":"\xf3","payload":{}}')
    job._handle_stdout_line(
        b'STEMLAB_EVENT {"protocol_version":2,"type":"completed","message":"done","payload":{}}'
    )
    assert failures
    assert "UTF-8 inv" in failures[0]
    assert "�" not in failures[0]
    assert not completions


def test_qprocess_dispatches_only_valid_progress_before_terminal_event(tmp_path: Path, qt_app) -> None:
    job = QProcessJob(tmp_path)
    observations = []
    job.progress_changed.connect(observations.append)
    observation = SeparationProgress("inference", 2, 5, 30).to_dict()
    job._handle_stdout_line(encode_event("progress", message="", payload=observation).encode())
    job._handle_stdout_line(encode_event("progress", message="", payload={"phase": "invalid"}).encode())
    job._handle_stdout_line(encode_event("completed", message="done").encode())
    job._handle_stdout_line(encode_event("progress", message="", payload=observation).encode())
    assert observations == [observation]


@pytest.mark.parametrize("payload", [
    {"result": {"error": {"details": {"reason": "unsupported encoding"}}}},
    {"reason": "unsupported encoding"},
])
def test_worker_failure_shows_underlying_reason(tmp_path: Path, qt_app, payload) -> None:
    job = QProcessJob(tmp_path)
    failures = []
    job.failed.connect(failures.append)
    job._handle_line(encode_event("failed", message="audio-separator failed.", payload=payload))
    assert failures == ["audio-separator failed. Detalhe: unsupported encoding"]
