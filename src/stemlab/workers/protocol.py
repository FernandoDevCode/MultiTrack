from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from stemlab.domain import DevicePolicy, OutputFormat, validate_requested_roles
from stemlab.domain.progress import SeparationProgress


PROTOCOL_VERSION = 2
EVENT_PREFIX = "STEMLAB_EVENT "


@dataclass(frozen=True)
class JobLaunch:
    input_path: Path
    mode_id: str
    output_dir: Path
    output_format: OutputFormat
    device_policy: DevicePolicy = DevicePolicy.AUTO
    requested_roles: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.requested_roles is not None:
            object.__setattr__(
                self, "requested_roles", validate_requested_roles(self.requested_roles)
            )


def build_worker_command(repo_root: Path, job: JobLaunch) -> tuple[str, list[str]]:
    root = repo_root.resolve()
    python_executable = root / ".venv" / "Scripts" / "python.exe"
    arguments = [
        "-X",
        "utf8",
        "-m",
        "stemlab.workers.run_job",
        "--input",
        str(job.input_path.resolve()),
        "--mode",
        job.mode_id,
        "--output",
        str(job.output_dir.resolve()),
        "--format",
        job.output_format.value.lower(),
        "--device",
        job.device_policy.value,
    ]
    for role in job.requested_roles or ():
        arguments.extend(("--stem", role))
    return str(python_executable), arguments


def encode_event(event_type: str, *, message: str, payload: dict[str, Any] | None = None) -> str:
    event = {
        "protocol_version": PROTOCOL_VERSION,
        "type": event_type,
        "message": message,
        "payload": payload or {},
    }
    return EVENT_PREFIX + json.dumps(event, ensure_ascii=False)


def parse_event_line(line: str) -> dict[str, Any] | None:
    if not line.startswith(EVENT_PREFIX):
        return None
    event = json.loads(line[len(EVENT_PREFIX) :])
    if event.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("Unsupported worker protocol version")
    if event.get("type") not in {"started", "status", "progress", "completed", "failed"}:
        raise ValueError("Unsupported worker event type")
    if not isinstance(event.get("message"), str) or not isinstance(event.get("payload"), dict):
        raise ValueError("Malformed worker event")
    if event["type"] == "progress":
        SeparationProgress(**event["payload"])
    return event
