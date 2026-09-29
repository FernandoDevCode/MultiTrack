from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stemlab.app import MODES, get_mode, new_output_dir
from stemlab.domain import OutputFormat
from stemlab.workers.protocol import JobLaunch
from stemlab.workers.qprocess_job import QProcessJob


class MainWindow(QMainWindow):
    def __init__(self, *, repo_root: Path | None = None, worker=None) -> None:
        super().__init__()
        self.repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self.worker = worker or QProcessJob(self.repo_root, self)
        self.input_path: Path | None = None
        self.output_dir: Path | None = None
        self._build_ui()
        self._connect_worker()
        self._set_idle_state()

    def _build_ui(self) -> None:
        self.setWindowTitle("StemLab v0.1")
        self.setMinimumSize(650, 390)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("StemLab")
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        subtitle = QLabel("Separação local de fontes musicais com CUDA")
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        file_row = QHBoxLayout()
        self.open_audio_button = QPushButton("Escolher música…")
        self.file_label = QLabel("Nenhum arquivo selecionado")
        self.file_label.setWordWrap(True)
        file_row.addWidget(self.open_audio_button)
        file_row.addWidget(self.file_label, 1)
        layout.addLayout(file_row)

        form = QFormLayout()
        self.mode_combo = QComboBox()
        for mode in MODES:
            self.mode_combo.addItem(mode.label, mode.mode_id)
        self.mode_combo.setCurrentIndex(1)
        self.format_combo = QComboBox()
        self.format_combo.addItem("WAV", OutputFormat.WAV)
        self.format_combo.addItem("FLAC", OutputFormat.FLAC)
        form.addRow("Modo", self.mode_combo)
        form.addRow("Formato", self.format_combo)
        layout.addLayout(form)

        self.mode_description = QLabel()
        self.mode_description.setWordWrap(True)
        self.mode_description.setStyleSheet("color: #555;")
        layout.addWidget(self.mode_description)

        self.separate_button = QPushButton("Separar")
        self.separate_button.setMinimumHeight(38)
        layout.addWidget(self.separate_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.open_folder_button = QPushButton("Abrir pasta dos stems")
        layout.addWidget(self.open_folder_button)
        layout.addStretch(1)
        self.setCentralWidget(central)

        self.open_audio_button.clicked.connect(self._choose_file)
        self.separate_button.clicked.connect(self.start_separation)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.mode_combo.currentIndexChanged.connect(self._update_mode_description)
        self._update_mode_description()

    def _connect_worker(self) -> None:
        self.worker.job_started.connect(lambda: self.status_label.setText("Processando na GPU…"))
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.completed.connect(self._job_completed)
        self.worker.failed.connect(self._job_failed)
        self.worker.job_finished.connect(self._worker_finished)

    def _choose_file(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher música",
            "",
            "Áudio (*.wav *.flac *.mp3 *.m4a *.aac *.ogg);;Todos os arquivos (*)",
        )
        if selected:
            self.set_input_path(Path(selected))

    def set_input_path(self, path: Path) -> None:
        self.input_path = path.resolve()
        self.file_label.setText(self.input_path.name)
        self.file_label.setToolTip(str(self.input_path))
        self.separate_button.setEnabled(self.input_path.is_file() and not self.worker.running)
        self.status_label.setText("Pronto para separar.")

    def start_separation(self) -> None:
        if self.input_path is None or not self.input_path.is_file():
            self._job_failed("Escolha um arquivo de áudio válido.")
            return
        mode_id = self.mode_combo.currentData()
        output_format = OutputFormat(self.format_combo.currentData())
        self.output_dir = new_output_dir(self.repo_root, self.input_path)
        launch = JobLaunch(
            input_path=self.input_path,
            mode_id=mode_id,
            output_dir=self.output_dir,
            output_format=output_format,
        )
        self._set_processing_state()
        try:
            self.worker.start(launch)
        except Exception as exc:
            self._job_failed(str(exc))

    def _set_idle_state(self) -> None:
        self.open_audio_button.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.separate_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self.open_folder_button.setEnabled(bool(self.output_dir and self.output_dir.is_dir()))
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        if self.input_path is None:
            self.status_label.setText("Escolha uma música para começar.")

    def _set_processing_state(self) -> None:
        self.open_audio_button.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.separate_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status_label.setText("Iniciando worker…")

    def _job_completed(self, payload: dict) -> None:
        result = payload.get("result", {})
        stems = result.get("stems", [])
        device = result.get("device") or {}
        self.output_dir = Path(payload["output_dir"]).resolve()
        self._set_idle_state()
        self.open_folder_button.setEnabled(True)
        self.status_label.setText(
            f"Concluído: {len(stems)} stems em {device.get('effective_device', 'device desconhecido')}."
        )

    def _job_failed(self, message: str) -> None:
        self._set_idle_state()
        self.open_folder_button.setEnabled(False)
        self.status_label.setText(f"Erro: {message}")

    def _worker_finished(self) -> None:
        self.open_audio_button.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.separate_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

    def _update_mode_description(self) -> None:
        mode = get_mode(self.mode_combo.currentData())
        self.mode_description.setText(mode.description)

    def open_output_folder(self) -> None:
        if self.output_dir and self.output_dir.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))
        else:
            QMessageBox.warning(self, "StemLab", "A pasta de saída ainda não existe.")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker.running:
            self.worker.stop()
        super().closeEvent(event)
