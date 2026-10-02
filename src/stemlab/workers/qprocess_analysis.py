from __future__ import annotations

from pathlib import Path

from stemlab.workers.analysis_protocol import AnalysisLaunch, build_analysis_worker_command
from stemlab.workers.qprocess_job import QProcessJob


class QProcessAnalysisJob(QProcessJob):
    def start(self, launch: AnalysisLaunch) -> None:
        if self.running:
            raise RuntimeError("An instrument analysis is already running")
        program, arguments = build_analysis_worker_command(self.repo_root, launch)
        if not Path(program).is_file():
            raise FileNotFoundError(f"Local analysis runtime not found: {program}")
        self._stdout_buffer = b""
        self._stderr_tail = ""
        self._terminal_event_received = False
        self.process.setProcessEnvironment(self._project_environment())
        self.process.start(program, arguments)
