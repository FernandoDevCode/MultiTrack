from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from stemlab.app.audio_extraction import (
    ExtractionRequest,
    ffmpeg_arguments,
    prepare_extraction,
    validate_extraction,
    monitor_arguments,
)
from stemlab.audio import probe_audio, sha256_file


class QProcessAudioExtraction(QObject):
    started = Signal()
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, repo_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.repo_root = repo_root.resolve()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.started.connect(self.started)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self._request: ExtractionRequest | None = None
        self._reported = False

    @property
    def running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def start(self, input_path: Path, output_path: Path) -> None:
        if self.running:
            raise RuntimeError("Já existe uma extração em andamento.")
        request = prepare_extraction(input_path, output_path)
        ffmpeg = self.repo_root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
        if not ffmpeg.is_file():
            raise FileNotFoundError(f"FFmpeg local não encontrado: {ffmpeg}")
        self._request = request
        self._reported = False
        self.process.start(str(ffmpeg), ffmpeg_arguments(request))

    def stop(self) -> None:
        if self.running:
            self.process.terminate()

    def _finished(self, exit_code: int, _status) -> None:
        if self._reported or self._request is None:
            return
        self._reported = True
        if exit_code != 0:
            detail = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace").strip()
            self._request.output_path.unlink(missing_ok=True)
            self.failed.emit(detail or f"FFmpeg encerrou com código {exit_code}.")
            return
        try:
            metadata = validate_extraction(self._request)
        except Exception as exc:
            self._request.output_path.unlink(missing_ok=True)
            self.failed.emit(str(exc))
            return
        self.completed.emit(metadata)

    def _process_error(self, _error) -> None:
        if not self._reported and self.process.state() == QProcess.ProcessState.NotRunning:
            self._reported = True
            self.failed.emit(self.process.errorString())


class QProcessMonitorCopy(QObject):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, repo_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.repo_root = repo_root.resolve()
        self.process = QProcess(self)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self._input: Path | None = None
        self._output: Path | None = None
        self._input_hash: str | None = None
        self._reported = False

    @property
    def running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def start(
        self,
        input_path: Path,
        output_path: Path,
        *,
        sample_rate: int,
        channels: int,
    ) -> None:
        if self.running:
            raise RuntimeError("Uma cópia de monitoramento já está em andamento.")
        source, target = input_path.resolve(), output_path.resolve()
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg = self.repo_root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
        if not ffmpeg.is_file():
            raise FileNotFoundError(ffmpeg)
        self._input, self._output = source, target
        self._input_hash = sha256_file(source)
        self._reported = False
        self.process.start(
            str(ffmpeg),
            monitor_arguments(source, target, sample_rate=sample_rate, channels=channels),
        )

    def stop(self) -> None:
        if self.running:
            self.process.terminate()

    def _finished(self, exit_code: int, _status) -> None:
        if self._reported or self._input is None or self._output is None:
            return
        self._reported = True
        try:
            if exit_code != 0:
                detail = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace").strip()
                raise RuntimeError(detail or f"FFmpeg encerrou com código {exit_code}.")
            metadata = probe_audio(self._output, validate_finite=True)
            if sha256_file(self._input) != self._input_hash:
                raise RuntimeError("O áudio original foi modificado durante a preparação.")
        except Exception as exc:
            self._output.unlink(missing_ok=True)
            self.failed.emit(str(exc))
            return
        self.completed.emit(metadata)

    def _process_error(self, _error) -> None:
        if not self._reported and self.process.state() == QProcess.ProcessState.NotRunning:
            self._reported = True
            self.failed.emit(self.process.errorString())
