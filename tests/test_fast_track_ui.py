from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
import pytest

from stemlab.ui import MainWindow


class FakeWorker(QObject):
    job_started = Signal()
    status_changed = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)
    job_finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.running = False
        self.last_job = None

    def start(self, job) -> None:
        self.last_job = job
        self.running = True
        self.job_started.emit()

    def stop(self) -> None:
        self.running = False


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_ui_basic_states_and_success(tmp_path: Path, qt_app, monkeypatch) -> None:
    input_path = tmp_path / "song.wav"
    input_path.write_bytes(b"fixture")
    worker = FakeWorker()
    window = MainWindow(repo_root=tmp_path, worker=worker)

    assert not window.separate_button.isEnabled()
    assert not window.open_folder_button.isEnabled()
    assert window.mode_combo.currentText() == "6 Stems"

    window.set_input_path(input_path)
    assert window.separate_button.isEnabled()
    window.start_separation()

    assert worker.last_job.mode_id == "six-stems"
    assert worker.last_job.output_format.value == "WAV"
    assert not window.separate_button.isEnabled()
    assert not window.mode_combo.isEnabled()
    assert window.progress.minimum() == 0 and window.progress.maximum() == 0

    worker.last_job.output_dir.mkdir(parents=True)
    worker.running = False
    worker.completed.emit(
        {
            "output_dir": str(worker.last_job.output_dir),
            "result": {
                "stems": [{"role": role} for role in ("vocals", "drums", "bass", "guitar", "piano", "other")],
                "device": {"effective_device": "cuda"},
            },
        }
    )
    assert window.separate_button.isEnabled()
    assert window.mode_combo.isEnabled()
    assert window.open_folder_button.isEnabled()
    assert "6 stems em cuda" in window.status_label.text()
    opened: list[str] = []
    monkeypatch.setattr(
        "stemlab.ui.main_window.QDesktopServices.openUrl",
        lambda url: opened.append(url.toLocalFile()) or True,
    )
    window.open_output_folder()
    assert len(opened) == 1
    assert Path(opened[0]).resolve() == worker.last_job.output_dir.resolve()
    window.close()


def test_ui_recovers_from_worker_error(tmp_path: Path, qt_app) -> None:
    input_path = tmp_path / "song.wav"
    input_path.write_bytes(b"fixture")
    worker = FakeWorker()
    window = MainWindow(repo_root=tmp_path, worker=worker)
    window.set_input_path(input_path)
    window.start_separation()
    worker.running = False
    worker.failed.emit("modelo ausente")

    assert window.separate_button.isEnabled()
    assert window.mode_combo.isEnabled()
    assert not window.open_folder_button.isEnabled()
    assert window.status_label.text() == "Erro: modelo ausente"
    window.close()


def test_launcher_uses_only_local_runtime() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    launcher = (repo_root / "START-STEMLAB.bat").read_text(encoding="utf-8")
    assert '.venv\\Scripts\\pythonw.exe" -m stemlab.ui' in launcher
    assert "tools\\ffmpeg\\bin" in launcher
    assert "winget" not in launcher.lower()
    assert "http" not in launcher.lower()
