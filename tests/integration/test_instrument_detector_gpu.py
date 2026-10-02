from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


def test_local_clap_analysis_runs_in_cuda_qprocess_and_exits(monkeypatch) -> None:
    if os.environ.get("STEMLAB_RUN_INSTRUMENT_SMOKE") != "1":
        pytest.skip("set STEMLAB_RUN_INSTRUMENT_SMOKE=1 to run the local CLAP smoke")

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QEventLoop, QProcess, QTimer
    from PySide6.QtWidgets import QApplication

    from stemlab.audio import sha256_file
    from stemlab.workers.analysis_protocol import AnalysisLaunch
    from stemlab.workers.qprocess_analysis import QProcessAnalysisJob

    repo_root = Path(__file__).resolve().parents[2]
    evidence = json.loads(
        (repo_root / ".tmp" / "phase0-smoke" / "latest-result.json").read_text(
            encoding="utf-8"
        )
    )
    input_path = Path(evidence["input"]["path"])
    input_hash = sha256_file(input_path)
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")

    app = QApplication.instance() or QApplication([])
    job = QProcessAnalysisJob(repo_root)
    payloads: list[dict] = []
    failures: list[str] = []
    heartbeats: list[int] = []
    loop = QEventLoop()
    heartbeat = QTimer()
    heartbeat.setInterval(50)
    heartbeat.timeout.connect(lambda: heartbeats.append(1))
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    job.completed.connect(payloads.append)
    job.failed.connect(failures.append)
    job.process.finished.connect(loop.quit)
    heartbeat.start()
    timeout.start(180_000)
    job.start(AnalysisLaunch(input_path))
    loop.exec()
    heartbeat.stop()
    timeout.stop()

    assert not failures, failures
    assert payloads, "CLAP analysis worker timed out"
    result = payloads[-1]["result"]
    assert result["effective_device"] == "cuda"
    assert result["input_path"] == str(input_path.resolve())
    assert result["input_sha256"] == input_hash == sha256_file(input_path)
    assert 1 <= len(result["windows"]) <= 8
    assert len(result["evidence"]) == 13
    assert result["peak_cuda_allocated_bytes"] > 0
    assert result["runtime_seconds"] > 0
    assert heartbeats
    assert job.process.state() == QProcess.ProcessState.NotRunning
    print(
        "CLAP smoke: "
        f"runtime={result['runtime_seconds']:.3f}s; "
        f"peak_allocated={result['peak_cuda_allocated_bytes']}; "
        f"peak_reserved={result['peak_cuda_reserved_bytes']}"
    )
