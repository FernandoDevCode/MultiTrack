from __future__ import annotations

from pathlib import Path
import math
import time

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QShowEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from stemlab.app import get_pipeline, new_output_dir
from stemlab.app.export_service import ExportError, ExportService
from stemlab.audio import MultiStemPlayer, probe_audio, supported_input_filter
from stemlab.domain import CORE_STEM_ROLES, DevicePolicy, OutputFormat
from stemlab.domain.progress import SeparationProgress
from stemlab.ui.branding import APP_NAME
from stemlab.ui.theme import APP_STYLESHEET, app_icon, control_icon
from stemlab.ui.workspace import build_workspace
from stemlab.ui.windows_chrome import apply_dark_title_bar
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
        self._progress_active = False
        self._progress_started = 0.0
        self._progress_phase = "preparing"
        self._eta_deadline: float | None = None
        self.setStyleSheet(APP_STYLESHEET)
        self.setWindowIcon(app_icon(self.repo_root))
        self._build_ui()
        if (self.repo_root / ".tmp/cpu-install-receipt.json").is_file():
            self.device_combo.setCurrentIndex(self.device_combo.findData(DevicePolicy.CPU_REQUIRED))
        self._connect_workers()
        self._set_idle_state()
        self._reset_progress()

    def _build_ui(self) -> None:
        build_workspace(self)

        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(100)
        self.playback_timer.timeout.connect(self._refresh_transport)
        self.playback_timer.start()

        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self._refresh_progress_time)

        self.open_audio_button.clicked.connect(self._choose_file)
        self.extract_audio_button.clicked.connect(self._choose_video_extraction)
        self.analyze_button.clicked.connect(self.start_instrument_analysis)
        self.separate_button.clicked.connect(self.start_separation)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.export_all_button.clicked.connect(self.export_all)
        self.stem_mixer.export_requested.connect(self.export_stem)
        self.mode_combo.currentIndexChanged.connect(self._update_mode_description)
        self.device_combo.currentIndexChanged.connect(self._update_device_hint)
        self.play_button.clicked.connect(self._toggle_playback)
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.seek_slider.sliderReleased.connect(self._seek_released)
        self.original_radio.toggled.connect(self._set_ab_mode)
        self.stems_radio.toggled.connect(self._set_ab_mode)
        self._update_mode_description()
        self._update_device_hint()

    def _connect_workers(self) -> None:
        self.worker.job_started.connect(
            lambda: self.status_label.setText("Processando separação no worker local…")
        )
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.progress_changed.connect(self._job_progress)
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
            supported_input_filter(),
        )
        if selected:
            self.set_input_path(Path(selected))

    def set_input_path(self, path: Path) -> None:
        self._release_result()
        self._reset_progress()
        self.instrument_panel.clear()
        self.analysis_group.setVisible(False)
        self.analyze_button.setText("Analisar instrumentos")
        self.input_path = path.resolve()
        output_format = {
            ".wav": OutputFormat.WAV,
            ".flac": OutputFormat.FLAC,
            ".mp3": OutputFormat.MP3,
        }.get(self.input_path.suffix.lower(), OutputFormat.WAV)
        self.format_combo.setCurrentIndex(self.format_combo.findData(output_format))
        self.file_label.setText(self.input_path.name)
        self.file_label.setToolTip(str(self.input_path))
        self._update_workspace_state()
        self.separate_button.setEnabled(self.input_path.is_file() and not self.worker.running)
        self._update_device_hint()
        self.status_label.setText("Pronto para separar.")

    def start_separation(self) -> None:
        if self.input_path is None or not self.input_path.is_file():
            self._job_failed("Escolha um arquivo de áudio válido.")
            return
        if self.analysis_worker.running:
            self._recoverable_error("Aguarde a análise de instrumentos terminar.")
            return
        pipeline = get_pipeline(self.mode_combo.currentData())
        if len(pipeline.steps) != 1:
            self._job_failed("Este checkpoint aceita somente pipelines de um passo.")
            return
        requested_roles = tuple(
            role for role, checkbox in self.stem_checkboxes.items() if checkbox.isChecked()
        )
        if not requested_roles:
            self._recoverable_error("Selecione ao menos uma faixa do Core Stems.")
            return
        output_format = OutputFormat(self.format_combo.currentData())
        device_policy = DevicePolicy(self.device_combo.currentData())
        self.output_dir = new_output_dir(self.repo_root, self.input_path)
        launch = JobLaunch(
            input_path=self.input_path,
            mode_id=pipeline.steps[0].mode_id,
            output_dir=self.output_dir,
            output_format=output_format,
            device_policy=device_policy,
            requested_roles=requested_roles,
        )
        self._set_processing_state()
        try:
            self.worker.start(launch)
        except Exception as exc:
            self._job_failed(str(exc))

    def _set_idle_state(self) -> None:
        self.open_audio_button.setEnabled(True)
        self.extract_audio_button.setEnabled(not self.extraction_job.running)
        analysis_allowed = (
            DevicePolicy(self.device_combo.currentData()) is not DevicePolicy.CPU_REQUIRED
        )
        self.analyze_button.setEnabled(
            analysis_allowed
            and bool(self.input_path and self.input_path.is_file())
            and not self.analysis_worker.running
        )
        self.mode_combo.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.device_combo.setEnabled(True)
        for checkbox in self.stem_checkboxes.values():
            checkbox.setEnabled(True)
        self.separate_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self.open_folder_button.setEnabled(bool(self.output_dir and self.output_dir.is_dir()))
        self.result_group.setVisible(bool(self.stems))
        self._update_workspace_state()
        if self.input_path is None:
            self.status_label.setText("Escolha uma música para começar.")

    def _set_processing_state(self) -> None:
        self._release_result()
        self.open_audio_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.format_combo.setEnabled(False)
        self.device_combo.setEnabled(False)
        for checkbox in self.stem_checkboxes.values():
            checkbox.setEnabled(False)
        self.separate_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self._start_progress()
        self._update_workspace_state(processing=True)
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
        self._finish_progress(success=True)
        self.open_folder_button.setEnabled(True)
        self.status_label.setText(
            f"Concluído: {len(stem_items)} stems em {device.get('effective_device', 'device desconhecido')}."
        )
        if len(stem_items) < len(CORE_STEM_ROLES):
            self.stems_radio.setToolTip(
                "Stems selecionados não formam uma reconstrução completa da mix original."
            )
        else:
            self.stems_radio.setToolTip("")
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
        self.stems_radio.setChecked(True)
        self.status_label.setText("Core Stems concluído e pronto para ouvir/exportar.")
        self._refresh_transport()

    def _job_failed(self, message: str) -> None:
        self._set_idle_state()
        self._finish_progress(success=False)
        self.open_folder_button.setEnabled(False)
        self.status_label.setText(f"Erro: {message}")

    def _worker_finished(self) -> None:
        self.open_audio_button.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.format_combo.setEnabled(True)
        self.device_combo.setEnabled(True)
        for checkbox in self.stem_checkboxes.values():
            checkbox.setEnabled(True)
        self.separate_button.setEnabled(bool(self.input_path and self.input_path.is_file()))
        self._update_device_hint()
        if self._progress_active:
            self._finish_progress(success=False)

    def _reset_progress(self) -> None:
        self._progress_active = False
        self._eta_deadline = None
        self.progress_timer.stop()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label.clear()
        self.eta_label.clear()
        self.progress_label.hide()
        self.eta_label.hide()

    def _start_progress(self) -> None:
        self._reset_progress()
        self._progress_active = True
        self._progress_started = time.perf_counter()
        self._progress_phase = "preparing"
        self.progress_label.show()
        self.eta_label.show()
        self.progress_label.setText("0% · Preparando separação…")
        self._refresh_progress_time()
        self.progress_timer.start()

    def _job_progress(self, payload: dict) -> None:
        if not self._progress_active:
            return
        try:
            observation = SeparationProgress(**payload)
        except (TypeError, ValueError):
            return
        self._progress_phase = observation.phase
        self._eta_deadline = (
            time.perf_counter() + observation.eta_seconds
            if observation.eta_seconds is not None else None
        )
        phases = {
            "preparing": "Validando entrada e modelo…",
            "loading": "Carregando modelo…",
            "inference": "Separando faixas…",
            "writing": "Gravando arquivos…",
            "validating": "Validando resultado…",
        }
        percent = max(self.progress.value(), observation.percent)
        self.progress.setValue(percent)
        self.progress_label.setText(f"{percent}% · {phases[observation.phase]}")
        self._refresh_progress_time()

    def _refresh_progress_time(self) -> None:
        if not self._progress_active:
            return
        now = time.perf_counter()
        elapsed = self._format_time(now - self._progress_started)
        if self._progress_phase in {"writing", "validating"}:
            remaining = "Finalizando arquivos…"
        elif self._eta_deadline is None:
            remaining = "Calculando estimativa…"
        elif self._eta_deadline <= now:
            remaining = "Recalculando estimativa…"
        else:
            seconds = math.ceil(self._eta_deadline - now)
            remaining = f"IA restante: ~{self._format_time(seconds)}"
        self.eta_label.setText(f"Decorrido: {elapsed}\n{remaining}")

    def _finish_progress(self, *, success: bool) -> None:
        was_active = self._progress_active
        self._progress_active = False
        self.progress_timer.stop()
        self._eta_deadline = None
        if not was_active:
            return
        if success:
            self.progress.setValue(100)
            self.progress_label.setText("100% · Separação concluída")
        else:
            self.progress_label.setText(f"{self.progress.value()}% · Separação interrompida")
        elapsed = self._format_time(time.perf_counter() - self._progress_started)
        self.eta_label.setText(f"Tempo decorrido: {elapsed}")

    def _update_mode_description(self) -> None:
        self.mode_description.setText(get_pipeline(self.mode_combo.currentData()).description)

    def _update_workspace_state(self, *, processing: bool = False) -> None:
        self.empty_panel.setVisible(processing or (not self.stems and not self.instrument_panel.has_analysis))
        if processing:
            self.empty_title.setText("Separando faixas")
            self.empty_description.setText("O processamento está em andamento. As faixas aparecerão aqui quando estiverem prontas.")
        elif self.input_path is not None:
            self.empty_title.setText("Pronto para separar")
            self.empty_description.setText("Escolha as faixas no painel à esquerda e clique em Separar.")
        else:
            self.empty_title.setText("Abra um arquivo de áudio")
            self.empty_description.setText("Escolha uma música para separar e ouvir cada instrumento.")

    def _update_device_hint(self) -> None:
        policy = DevicePolicy(self.device_combo.currentData())
        has_input = bool(self.input_path and self.input_path.is_file())
        if policy is DevicePolicy.CPU_REQUIRED:
            self.device_hint.setText(
                "CPU selecionada: a separação pode ser lenta e usará FP32. "
                "A análise automática CLAP está indisponível em CPU nesta versão."
            )
            self.analyze_button.setEnabled(False)
        elif policy is DevicePolicy.AUTO:
            self.device_hint.setText(
                "Automático usa CUDA quando disponível; caso contrário usa CPU em FP32, "
                "que pode ser lenta."
            )
            self.analyze_button.setEnabled(has_input and not self.analysis_worker.running)
        else:
            self.device_hint.setText("CUDA é obrigatória; não haverá fallback silencioso para CPU.")
            self.analyze_button.setEnabled(has_input and not self.analysis_worker.running)

    def start_instrument_analysis(self) -> None:
        if self.input_path is None or not self.input_path.is_file():
            self._recoverable_error("Escolha um arquivo de áudio válido.")
            return
        if DevicePolicy(self.device_combo.currentData()) is DevicePolicy.CPU_REQUIRED:
            self._recoverable_error(
                "Análise automática indisponível em CPU nesta versão; "
                "a separação Core continua disponível."
            )
            return
        if self.worker.running:
            self._recoverable_error("Aguarde a separação terminar.")
            return
        self.open_audio_button.setEnabled(False)
        self.extract_audio_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.separate_button.setEnabled(False)
        self._reset_progress()
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
        self._update_workspace_state()
        self.workspace_scroll.verticalScrollBar().setValue(0)
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
        self._update_device_hint()
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
        button_text = "Pause" if state.playing else "Play"
        if self.play_button.text() != button_text:
            self.play_button.setText(button_text)
            self.play_button.setShortcut("Ctrl+Space")
        self.play_button.setIcon(control_icon("pause" if state.playing else "play"))
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
            QMessageBox.warning(self, APP_NAME, "A pasta de saída ainda não existe.")

    def _release_result(self) -> None:
        self.player.close()
        self.stem_mixer.clear()
        self.stems = {}
        self._pending_stems = {}
        self.result_group.setVisible(False)
        self._update_workspace_state()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        apply_dark_title_bar(self)

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
