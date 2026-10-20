from __future__ import annotations

import importlib.util
from pathlib import Path


def _doctor_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("stemlab_doctor_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cpu_profile_skips_nvidia_clap_and_specialists(monkeypatch) -> None:
    doctor = _doctor_module()
    calls: list[tuple[str, str | None]] = []
    monkeypatch.setattr(doctor, "check_python", lambda: calls.append(("python", None)))
    monkeypatch.setattr(doctor, "check_local_environment", lambda: calls.append(("env", None)))
    monkeypatch.setattr(doctor, "check_nvidia_smi", lambda: calls.append(("nvidia", None)))
    monkeypatch.setattr(doctor, "check_torch", lambda profile: calls.append(("torch", profile)))
    monkeypatch.setattr(doctor, "check_audio_separator", lambda: calls.append(("separator", None)))
    monkeypatch.setattr(doctor, "check_pyside", lambda: calls.append(("pyside", None)))
    monkeypatch.setattr(doctor, "check_sounddevice", lambda: calls.append(("sounddevice", None)))
    monkeypatch.setattr(doctor, "check_transformers_and_detector", lambda: calls.append(("clap", None)))
    monkeypatch.setattr(doctor, "check_local_tool", lambda name: calls.append((name, None)))
    monkeypatch.setattr(doctor, "check_smoke_model", lambda profile: calls.append(("model", profile)))
    monkeypatch.setattr(doctor, "check_specialist_candidates", lambda: calls.append(("specialists", None)))

    assert doctor.main(["--profile", "cpu"]) == 0

    assert ("torch", "cpu") in calls
    assert ("model", "cpu") in calls
    assert ("nvidia", None) not in calls
    assert ("clap", None) not in calls
    assert ("specialists", None) not in calls


def test_default_doctor_profile_remains_gpu() -> None:
    doctor = _doctor_module()
    assert doctor.build_parser().parse_args([]).profile == "gpu"
