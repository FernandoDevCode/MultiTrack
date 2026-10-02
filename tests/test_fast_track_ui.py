from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication
import numpy as np
import pytest
import soundfile as sf

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


class FakeAnalysisWorker(QObject):
    job_started = Signal()
    status_changed = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)
    job_finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.running = False
        self.last_launch = None

    def start(self, launch) -> None:
        self.last_launch = launch
        self.running = True
        self.job_started.emit()
        QTimer.singleShot(20, self._complete)

    def _complete(self) -> None:
        targets = (
            "vocals", "drums", "bass", "guitar", "piano", "keys", "synth_pad",
            "organ", "percussion", "strings", "brass", "woodwind", "choir",
        )
        self.completed.emit(
            {
                "result": {
                    "runtime_seconds": 0.01,
                    "effective_device": "cuda",
                    "evidence": [
                        {
                            "target_id": target,
                            "state": "suggested" if index < 5 else "not_suggested",
                        }
                        for index, target in enumerate(targets)
                    ],
                }
            }
        )
        self.running = False
        self.job_finished.emit()

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
    assert window.mode_combo.currentText() == "Core Stems"

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


def test_completed_core_stems_shows_one_synchronized_mixer(tmp_path: Path, qt_app) -> None:
    input_path = tmp_path / "song.wav"
    audio = np.zeros((1000, 2), dtype=np.float32)
    sf.write(input_path, audio, 1000, subtype="FLOAT")
    output_dir = tmp_path / "outputs" / "run"
    output_dir.mkdir(parents=True)
    stem_items = []
    for index, role in enumerate(("vocals", "drums", "bass", "guitar", "piano", "other")):
        path = output_dir / f"{role}.wav"
        sf.write(path, audio + (index + 1) / 100, 1000, subtype="FLOAT")
        stem_items.append(
            {"role": role, "path": str(path), "sample_rate": 1000, "channels": 2}
        )
    worker = FakeWorker()
    window = MainWindow(repo_root=tmp_path, worker=worker)
    window.set_input_path(input_path)
    window.start_separation()
    worker.running = False
    worker.completed.emit(
        {
            "output_dir": str(output_dir),
            "result": {"stems": stem_items, "device": {"effective_device": "cuda"}},
        }
    )
    assert not window.result_group.isHidden()
    assert len(window.stem_mixer.rows) == 6
    assert window.original_radio.text() == "Original"
    assert window.stems_radio.isChecked()
    assert window.export_all_button.text() == "Exportar todos"
    assert window.player.state().total_frames == 1000
    window.close()


def test_instrument_analysis_is_responsive_editable_and_does_not_auto_separate(
    tmp_path: Path, qt_app
) -> None:
    input_path = tmp_path / "Música São João - João & Núbia.wav"
    input_path.write_bytes(b"fixture")
    separation_worker = FakeWorker()
    analysis_worker = FakeAnalysisWorker()
    window = MainWindow(
        repo_root=tmp_path,
        worker=separation_worker,
        analysis_worker=analysis_worker,
    )
    window.set_input_path(input_path)
    heartbeats: list[int] = []
    heartbeat = QTimer()
    heartbeat.setInterval(1)
    heartbeat.timeout.connect(lambda: heartbeats.append(1))
    loop = QEventLoop()
    analysis_worker.job_finished.connect(loop.quit)
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    heartbeat.start()
    timeout.start(2_000)
    window.start_instrument_analysis()
    loop.exec()
    heartbeat.stop()
    timeout.stop()

    assert heartbeats
    assert analysis_worker.last_launch.input_path == input_path.resolve()
    assert separation_worker.last_job is None
    assert window.instrument_panel.has_analysis
    assert not window.analysis_group.isHidden()
    assert window.analyze_button.text() == "Reanalisar instrumentos"
    assert len(window.instrument_panel.current_plan().steps) == 1
    for checkbox in window.instrument_panel.checkboxes.values():
        checkbox.setChecked(False)
    window.instrument_panel.checkboxes["strings"].setChecked(True)
    assert window.instrument_panel.current_plan().steps == ()
    assert "especializado" in window.instrument_panel.plan_summary.text().lower()
    for target in ("vocals", "drums", "bass", "guitar", "piano"):
        window.instrument_panel.checkboxes[target].setChecked(True)
    assert len(window.instrument_panel.current_plan().steps) == 1
    window.close()


def test_ui_never_describes_detector_scores_as_percent_confidence() -> None:
    ui_root = Path(__file__).resolve().parents[1] / "src" / "stemlab" / "ui"
    source = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.glob("*.py"))
    lowered = source.lower()
    assert "confidence" not in lowered
    assert "probability" not in lowered
    assert "% confidence" not in lowered


def test_launcher_uses_only_local_runtime() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    launcher = (repo_root / "START-STEMLAB.bat").read_text(encoding="utf-8")
    assert '.venv\\Scripts\\pythonw.exe" -m stemlab.ui' in launcher
    assert "tools\\ffmpeg\\bin" in launcher
    assert "winget" not in launcher.lower()
    assert "http" not in launcher.lower()
