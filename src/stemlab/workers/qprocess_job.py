from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from stemlab.workers.protocol import JobLaunch, build_worker_command, parse_event_line


_EVENT_PREFIX_BYTES = b"STEMLAB_EVENT "


class QProcessJob(QObject):
    job_started = Signal()
    status_changed = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)
    job_finished = Signal()

    def __init__(self, repo_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.repo_root = repo_root.resolve()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.setWorkingDirectory(str(self.repo_root))
        self.process.started.connect(self.job_started)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self._stdout_buffer = b""
        self._stderr_tail = ""
        self._terminal_event_received = False

    @property
    def running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def start(self, job: JobLaunch) -> None:
        if self.running:
            raise RuntimeError("A separation job is already running")
        program, arguments = build_worker_command(self.repo_root, job)
        if not Path(program).is_file():
            raise FileNotFoundError(f"Local worker runtime not found: {program}")
        self._stdout_buffer = b""
        self._stderr_tail = ""
        self._terminal_event_received = False
        self.process.setProcessEnvironment(self._project_environment())
        self.process.start(program, arguments)

    def stop(self) -> None:
        if self.running:
            self.process.terminate()

    def _project_environment(self) -> QProcessEnvironment:
        environment = QProcessEnvironment.systemEnvironment()
        local_paths = {
            "TEMP": self.repo_root / ".tmp",
            "TMP": self.repo_root / ".tmp",
            "PIP_CACHE_DIR": self.repo_root / ".cache" / "pip",
            "TORCH_HOME": self.repo_root / ".cache" / "torch",
            "HF_HOME": self.repo_root / ".cache" / "huggingface",
            "XDG_CACHE_HOME": self.repo_root / ".cache",
            "MPLCONFIGDIR": self.repo_root / ".cache" / "matplotlib",
            "AUDIO_SEPARATOR_MODEL_DIR": self.repo_root / "models",
        }
        for key, path in local_paths.items():
            path.mkdir(parents=True, exist_ok=True)
            environment.insert(key, str(path))
        environment.insert("PYTHONUTF8", "1")
        environment.insert("PYTHONIOENCODING", "utf-8:strict")
        path_value = environment.value("PATH")
        environment.insert(
            "PATH",
            os.pathsep.join(
                [
                    str(self.repo_root / "tools" / "ffmpeg" / "bin"),
                    str(self.repo_root / ".venv" / "Scripts"),
                    path_value,
                ]
            ),
        )
        return environment

    def _read_stdout(self) -> None:
        self._stdout_buffer += bytes(self.process.readAllStandardOutput())
        lines = self._stdout_buffer.split(b"\n")
        self._stdout_buffer = lines.pop()
        for line in lines:
            self._handle_stdout_line(line.rstrip(b"\r"))

    def _handle_stdout_line(self, line: bytes) -> None:
        if self._terminal_event_received:
            return
        if not line.startswith(_EVENT_PREFIX_BYTES):
            return
        try:
            decoded = line.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            self._protocol_decode_failed(exc)
            return
        self._handle_line(decoded)

    def _protocol_decode_failed(self, error: UnicodeDecodeError) -> None:
        self._terminal_event_received = True
        self.failed.emit(
            "Worker protocol contém UTF-8 inválido; o resultado não foi carregado. "
            f"Posição do byte: {error.start}."
        )

    def _handle_line(self, line: str) -> None:
        try:
            event = parse_event_line(line)
        except (ValueError, TypeError):
            return
        if event is None:
            return
        event_type = event["type"]
        if event_type == "status":
            self.status_changed.emit(event["message"])
        elif event_type == "completed":
            self._terminal_event_received = True
            self.completed.emit(event["payload"])
        elif event_type == "failed":
            self._terminal_event_received = True
            self.failed.emit(event["message"])

    def _read_stderr(self) -> None:
        chunk = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self._stderr_tail = (self._stderr_tail + chunk)[-8_000:]

    def _finished(self, exit_code: int, _exit_status) -> None:
        if self._stdout_buffer:
            self._handle_stdout_line(self._stdout_buffer.rstrip(b"\r"))
            self._stdout_buffer = b""
        if not self._terminal_event_received:
            detail = self._stderr_tail.strip().splitlines()
            suffix = f" Detalhe: {detail[-1]}" if detail else ""
            self.failed.emit(f"Worker encerrou com código {exit_code}.{suffix}")
        self.job_finished.emit()

    def _process_error(self, _error) -> None:
        if not self._terminal_event_received and self.process.state() == QProcess.ProcessState.NotRunning:
            self._terminal_event_received = True
            self.failed.emit(self.process.errorString())
