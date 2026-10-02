from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from stemlab.app import PIPELINES, get_pipeline, new_output_dir
from stemlab.app.export_service import ExportError, ExportService
from stemlab.audio import MultiStemPlayer, probe_audio
from stemlab.domain import OutputFormat
from stemlab.ui.stem_mixer import StemMixer
from stemlab.ui.instrument_analysis_panel import InstrumentAnalysisPanel
from stemlab.workers.analysis_protocol import AnalysisLaunch
from stemlab.workers.protocol import JobLaunch
from stemlab.workers.qprocess_analysis import QProcessAnalysisJob
from stemlab.workers.qprocess_audio import QProcessAudioExtraction, QProcessMonitorCopy
from stemlab.workers.qprocess_job import QProcessJob


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        worker=None,
        player=None,
        analysis_worker=None,
    ) -> None:
        super().__init__()
        self.repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self.worker = worker or QProcessJob(self.repo_root, self)
        self.analysis_worker = analysis_worker or QProcessAnalysisJob(self.repo_root, self)
        self.player = player or MultiStemPlayer()
        self.export_service = ExportService()
        self.extraction_job = QProcessAudioExtraction(self.repo_root, self)
        self.monitor_job = QProcessMonitorCopy(self.repo_root, self)
        self.input_path: Path | None = None
        self.output_dir: Path | None = None
        self.stems: dict[str, Path] = {}
        self._pending_stems: dict[str, Path] = {}
        self._seeking = False
        self._build_ui()
        self._connect_workers()
        self._set_idle_state()

    def _build_ui(self) -> None:
        self.setWindowTitle("StemLab v0.2 — Core Stems")
        self.setMinimumSize(720, 650)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        title = QLabel("StemLab")
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        layout.addWidget(title)

        file_row = QHBoxLayout()
        self.open_audio_button = QPushButton("Escolher música…")
        self.extract_audio_button = QPushButton("Extrair áudio de vídeo…")
        self.analyze_button = QPushButton("Analisar instrumentos")
        self.file_label = QLabel("Nenhum arquivo selecionado")
        self.file_label.setWordWrap(True)
        file_row.addWidget(self.open_audio_button)
        file_row.addWidget(self.extract_audio_button)
        file_row.addWidget(self.analyze_button)
        file_row.addWidget(self.file_label, 1)
        layout.addLayout(file_row)

        form = QFormLayout()
        self.mode_combo = QComboBox()
        for pipeline in PIPELINES:
            self.mode_combo.addItem(pipeline.label, pipeline.pipeline_id)
        self.format_combo = QComboBox()
        self.format_combo.addItem("WAV", OutputFormat.WAV)
        self.format_combo.addItem("FLAC", OutputFormat.FLAC)
        form.addRow("Preset", self.mode_combo)
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

        self.analysis_group = QGroupBox("Análise de instrumentos")
        analysis_layout = QVBoxLayout(self.analysis_group)
        self.instrument_panel = InstrumentAnalysisPanel(self.analysis_group)
        analysis_layout.addWidget(self.instrument_panel)
        layout.addWidget(self.analysis_group)
        self.analysis_group.setVisible(False)

        self.result_group = QGroupBox("Player sincronizado")
        result_layout = QVBoxLayout(self.result_group)
        transport = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.time_label = QLabel("00:00 / 00:00")
        transport.addWidget(self.play_button)
        transport.addWidget(self.seek_slider, 1)
        transport.addWidget(self.time_label)
        result_layout.addLayout(transport)

        ab_row = QHBoxLayout()
        ab_row.addWidget(QLabel("Monitor:"))
        self.original_radio = QRadioButton("Original")
        self.stems_radio = QRadioButton("Stems")
        self.stems_radio.setChecked(True)
        self.ab_group = QButtonGroup(self)
        self.ab_group.setExclusive(True)
        self.ab_group.addButton(self.original_radio)
        self.ab_group.addButton(self.stems_radio)
        ab_row.addWidget(self.original_radio)
        ab_row.addWidget(self.stems_radio)
        ab_row.addStretch(1)
        result_layout.addLayout(ab_row)

        self.stem_mixer = StemMixer(self.player, self)
        result_layout.addWidget(self.stem_mixer)
        actions = QHBoxLayout()
        self.export_all_button = QPushButton("Exportar todos")
        self.open_folder_button = QPushButton("Abrir pasta")
        actions.addWidget(self.export_all_button)
        actions.addWidget(self.open_folder_button)
        actions.addStretch(1)
        result_layout.addLayout(actions)
        layout.addWidget(self.result_group)
        layout.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(100)
        self.playback_timer.timeout.connect(self._refresh_transport)
        self.playback_timer.start()

        self.open_audio_button.clicked.connect(self._choose_file)
        self.extract_audio_button.clicked.connect(self._choose_video_extraction)
        self.analyze_button.clicked.connect(self.start_instrument_analysis)
        self.separate_button.clicked.connect(self.start_separation)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.export_all_button.clicked.connect(self.export_all)
        self.stem_mixer.export_requested.connect(self.export_stem)
        self.mode_combo.currentIndexChanged.connect(self._update_mode_description)
        self.play_button.clicked.connect(self._toggle_playback)
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.seek_slider.sliderReleased.connect(self._seek_released)
        self.original_radio.toggled.connect(self._set_ab_mode)
        self.stems_radio.toggled.connect(self._set_ab_mode)
        self._update_mode_description()

    def _connect_workers(self) -> None:
        self.worker.job_started.connect(lambda: self.status_label.setText("Processando na GPU…"))
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.completed.connect(self._job_completed)
        self.worker.failed.connect(self._job_failed)
        self.worker.job_finished.connect(self._worker_finished)
        self.extraction_job.started.connect(
            lambda: self.status_label.setText("Extraindo áudio com FFmpeg local…")
        )
        self.extraction_job.completed.connect(self._extraction_completed)
        self.extraction_job.failed.connect(self._recoverable_error)
        self.monitor_job.completed.connect(lambda metadata: self._load_player(Path(metadata.path)))
        self.monitor_job.failed.connect(self._recoverable_error)
        self.analysis_worker.job_started.connect(
            lambda: self.status_label.setText("Analisando janelas com CLAP local em CUDA…")
        )
        self.analysis_worker.status_changed.connect(self.status_label.setText)
        self.analysis_worker.completed.connect(self._analysis_completed)
        self.analysis_worker.failed.connect(self._analysis_failed)
        self.analysis_worker.job_finished.connect(self._analysis_finished)

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
        self._release_result()
        self.instrument_panel.clear()
        self.analysis_group.setVisible(False)
        self.analyze_button.setText("Analisar instrumentos")
        self.input_path = path.resolve()
        self.file_label.setText(self.input_path.name)
        self.file_label.setToolTip(str(self.input_path))
        self.separate_button.setEnabled(self.input_path.is_file() and not self.worker.running)
        self.status_label.setText("Pronto para separar.")

    def start_separation(self) -> None:
        if self.input_path is None or not self.input_path.is_file():
            self._job_failed("Escolha um arquivo de áudio válido.")
            return
        if self.analysis_worker.running:
            self._recoverable_error("Aguarde a análise de instrumentos terminar.")
            return
        pipeline = (
            self.instrument_panel.current_plan()
            if self.instrument_panel.has_analysis
            else get_pipeline(self.mode_combo.currentData())
        )
        if self.instrument_panel.has_analysis and not pipeline.confirmed_targets:
            self._recoverable_error("Confirme ao menos um instrumento antes de usar o plano analisado.")
            return
        if self.instrument_panel.has_analysis and not pipeline.steps:
            self._recoverable_error(
                "Os instrumentos confirmados ainda não possuem separador especializado."
            )
            return
        if len(pipeline.steps) != 1:
            self._job_failed("Este checkpoint aceita somente pipelines de um passo.")
            return
        output_format = OutputFormat(self.format_combo.currentData())
        self.output_dir = new_output_dir(self.repo_root, self.input_path)
        launch = JobLaunch(
            input_path=self.input_path,
            mode_id=pipeline.steps[0].mode_id,
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
        self.extract_audio_button.setEnabled(not self.extraction_job.running)
        self.analyze_button.setEnabled(
            bool(self.input_path and self.input_path.is_file()) and not self.analysis_worker.running
        )
        self.mode_combo.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.separate_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self.open_folder_button.setEnabled(bool(self.output_dir and self.output_dir.is_dir()))
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.result_group.setVisible(bool(self.stems))
        if self.input_path is None:
            self.status_label.setText("Escolha uma música para começar.")

    def _set_processing_state(self) -> None:
        self._release_result()
        self.open_audio_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.separate_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status_label.setText("Iniciando worker…")

    def _job_completed(self, payload: dict) -> None:
        result = payload.get("result", {})
        stem_items = result.get("stems", [])
        device = result.get("device") or {}
        self.output_dir = Path(payload["output_dir"]).resolve()
        self.stems = {
            item["role"]: Path(item["path"]).resolve()
            for item in stem_items
            if item.get("role") and item.get("path")
        }
        self._set_idle_state()
        self.open_folder_button.setEnabled(True)
        self.status_label.setText(
            f"Concluído: {len(stem_items)} stems em {device.get('effective_device', 'device desconhecido')}."
        )
        if self.stems and self.input_path:
            self._prepare_player(result)

    def _prepare_player(self, result: dict) -> None:
        self._pending_stems = self.stems.copy()
        stem = result["stems"][0]
        try:
            original = probe_audio(self.input_path)
            compatible = original.sample_rate == stem["sample_rate"] and original.channels == stem["channels"]
        except Exception:
            compatible = False
        if compatible:
            self._load_player(self.input_path)
            return
        monitor_path = self.output_dir / "original-monitor.flac"
        self.status_label.setText("Preparando cópia lossless do original para monitoramento…")
        try:
            self.monitor_job.start(
                self.input_path,
                monitor_path,
                sample_rate=int(stem["sample_rate"]),
                channels=int(stem["channels"]),
            )
        except Exception as exc:
            self._recoverable_error(str(exc))

    def _load_player(self, original_path: Path) -> None:
        try:
            self.player.load_session(self._pending_stems, original=original_path)
        except Exception as exc:
            self._recoverable_error(f"Player indisponível: {exc}")
            return
        self.stem_mixer.set_stems(self._pending_stems)
        self.result_group.setVisible(True)
        self.play_button.setText("Play")
        self.stems_radio.setChecked(True)
        self.status_label.setText("Core Stems concluído e pronto para ouvir/exportar.")
        self._refresh_transport()

    def _job_failed(self, message: str) -> None:
        self._set_idle_state()
        self.open_folder_button.setEnabled(False)
        self.status_label.setText(f"Erro: {message}")

    def _worker_finished(self) -> None:
        self.open_audio_button.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.separate_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self.analyze_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

    def _update_mode_description(self) -> None:
        self.mode_description.setText(get_pipeline(self.mode_combo.currentData()).description)

    def start_instrument_analysis(self) -> None:
        if self.input_path is None or not self.input_path.is_file():
            self._recoverable_error("Escolha um arquivo de áudio válido.")
            return
        if self.worker.running:
            self._recoverable_error("Aguarde a separação terminar.")
            return
        self.open_audio_button.setEnabled(False)
        self.extract_audio_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.separate_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status_label.setText("Iniciando análise de instrumentos…")
        try:
            self.analysis_worker.start(AnalysisLaunch(self.input_path))
        except Exception as exc:
            self._analysis_failed(str(exc))
            self._analysis_finished()

    def _analysis_completed(self, payload: dict) -> None:
        result = payload["result"]
        self.instrument_panel.set_result(result)
        self.analysis_group.setVisible(True)
        self.analyze_button.setText("Reanalisar instrumentos")
        self.status_label.setText(
            f"Sugestões concluídas em {result['runtime_seconds']:.2f}s usando "
            f"{result['effective_device']}; confirme ou corrija a lista."
        )

    def _analysis_failed(self, message: str) -> None:
        self.status_label.setText(f"Erro recuperável na análise: {message}")

    def _analysis_finished(self) -> None:
        self.open_audio_button.setEnabled(True)
        self.extract_audio_button.setEnabled(not self.extraction_job.running)
        self.analyze_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self.separate_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

    def _toggle_playback(self) -> None:
        try:
            if self.player.state().playing:
                self.player.pause()
            else:
                self.player.play()
        except Exception as exc:
            self._recoverable_error(str(exc))
        self._refresh_transport()

    def _set_ab_mode(self) -> None:
        if not self.stems:
            return
        try:
            self.player.set_mode("original" if self.original_radio.isChecked() else "stems")
        except Exception as exc:
            self._recoverable_error(str(exc))

    def _seek_released(self) -> None:
        state = self.player.state()
        self.player.seek(state.duration_seconds * self.seek_slider.value() / 1000.0)
        self._seeking = False
        self._refresh_transport()

    def _refresh_transport(self) -> None:
        state = self.player.state()
        self.play_button.setText("Pause" if state.playing else "Play")
        if not self._seeking and state.total_frames:
            self.seek_slider.setValue(round(1000 * state.frame / state.total_frames))
        self.time_label.setText(
            f"{self._format_time(state.current_seconds)} / {self._format_time(state.duration_seconds)}"
        )

    @staticmethod
    def _format_time(seconds: float) -> str:
        total = max(0, round(seconds))
        return f"{total // 60:02d}:{total % 60:02d}"

    def export_stem(self, role: str, path: Path) -> None:
        selected, _ = QFileDialog.getSaveFileName(
            self, f"Exportar {role.title()}", path.name, f"Áudio (*{path.suffix})"
        )
        if not selected:
            return
        try:
            target = self.export_service.export_one(path, Path(selected))
            self.status_label.setText(f"Stem exportado e validado: {target}")
        except (ExportError, OSError) as exc:
            self._recoverable_error(str(exc))

    def export_all(self) -> None:
        parent = QFileDialog.getExistingDirectory(self, "Escolher pasta para a nova exportação")
        if not parent or not self.output_dir:
            return
        destination = Path(parent) / f"{self.output_dir.name}-export"
        try:
            paths = self.export_service.export_all(self.stems, destination)
            self.status_label.setText(f"{len(paths)} stems exportados e validados em {destination}.")
        except (ExportError, OSError) as exc:
            self._recoverable_error(str(exc))

    def _choose_video_extraction(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self, "Extrair áudio de vídeo", "", "Vídeo (*.mp4 *.mkv *.mov *.webm *.avi *.m4v)"
        )
        if not source:
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Salvar áudio lossless", str(Path(source).with_suffix(".flac")), "FLAC (*.flac);;WAV (*.wav)"
        )
        if not target:
            return
        try:
            self.extraction_job.start(Path(source), Path(target))
            self.extract_audio_button.setEnabled(False)
        except Exception as exc:
            self._recoverable_error(str(exc))

    def _extraction_completed(self, metadata) -> None:
        self.extract_audio_button.setEnabled(True)
        self.status_label.setText(
            f"Áudio extraído e validado: {metadata.path} ({metadata.sample_rate} Hz, {metadata.channels} canais)."
        )

    def _recoverable_error(self, message: str) -> None:
        self.extract_audio_button.setEnabled(not self.extraction_job.running)
        self.status_label.setText(f"Erro recuperável: {message}")

    def open_output_folder(self) -> None:
        if self.output_dir and self.output_dir.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir)))
        else:
            QMessageBox.warning(self, "StemLab", "A pasta de saída ainda não existe.")

    def _release_result(self) -> None:
        self.player.close()
        self.stem_mixer.clear()
        self.stems = {}
        self._pending_stems = {}
        self.result_group.setVisible(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker.running:
            self.worker.stop()
        if self.extraction_job.running:
            self.extraction_job.stop()
        if self.monitor_job.running:
            self.monitor_job.stop()
        if self.analysis_worker.running:
            self.analysis_worker.stop()
        self.player.close()
        super().closeEvent(event)
