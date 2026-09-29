from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


def test_six_stems_end_to_end_through_ui_and_qprocess(monkeypatch) -> None:
    if os.environ.get("STEMLAB_RUN_FAST_TRACK_SMOKE") != "1":
        pytest.skip("set STEMLAB_RUN_FAST_TRACK_SMOKE=1 to run the Fast Track UI smoke")

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication

    from stemlab.audio import sha256_file
    from stemlab.ui import MainWindow

    repo_root = Path(__file__).resolve().parents[2]
    evidence = json.loads(
        (repo_root / ".tmp" / "phase0-smoke" / "latest-result.json").read_text(
            encoding="utf-8"
        )
    )
    input_path = Path(evidence["input"]["path"])
    input_hash = sha256_file(input_path)

    # If the backend attempts network after installation, this smoke must fail.
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")

    app = QApplication.instance() or QApplication([])
    window = MainWindow(repo_root=repo_root)
    window.set_input_path(input_path)
    window.format_combo.setCurrentIndex(1)  # FLAC

    payloads: list[dict] = []
    failures: list[str] = []
    heartbeats: list[int] = []
    loop = QEventLoop()
    heartbeat = QTimer()
    heartbeat.setInterval(50)
    heartbeat.timeout.connect(lambda: heartbeats.append(1))
    heartbeat.start()
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(120_000)
    window.worker.completed.connect(payloads.append)
    window.worker.failed.connect(failures.append)
    window.worker.process.finished.connect(loop.quit)

    window.start_separation()
    loop.exec()
    heartbeat.stop()
    timeout.stop()

    assert not failures, failures
    assert payloads, "worker timed out before a completed event"
    result = payloads[-1]["result"]
    assert result["success"] is True
    assert result["device"]["effective_device"] == "cuda"
    assert {stem["role"] for stem in result["stems"]} == {
        "vocals",
        "drums",
        "bass",
        "guitar",
        "piano",
        "other",
    }
    assert all(stem["format"] == "FLAC" for stem in result["stems"])
    assert Path(result["manifest_path"]).is_file()
    assert sha256_file(input_path) == input_hash
    assert len(heartbeats) >= 20, "UI event loop did not remain responsive"
    assert window.open_folder_button.isEnabled()
    assert window.separate_button.isEnabled()
    window.close()
