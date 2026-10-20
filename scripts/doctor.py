from __future__ import annotations

import argparse
import importlib.metadata
import hashlib
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON = (3, 12, 10)
EXPECTED_TORCH = "2.8.0+cu128"
EXPECTED_GPU = "NVIDIA GeForce RTX 5060"
GPU_ONLY_MODEL_FILES = {
    "model_bs_roformer_ep_317_sdr_12.9755.ckpt": (
        639_331_213,
        "5b84f37e8d444c8cb30c79d77f613a41c05868ff9c9ac6c7049c00aefae115aa",
    ),
    "model_bs_roformer_ep_317_sdr_12.9755.yaml": (
        2_273,
        "2bfdd16c656bd9519aba757cc4f8834b7ede675eb1e00ec4772d74ae1c41af7f",
    ),
}
CORE_MODEL_FILES = {
    "BS-Roformer-SW.ckpt": (
        699_412_152,
        "24e7d35ee9c64415673d3fd33e06a67cac2c103c5df6267ba1576459c775916e",
    ),
    "BS-Roformer-SW.yaml": (
        4_653,
        "b558996f1e25eb48798bd6502505a5de94c4f966d6edfb1a0420f06cc40b501a",
    ),
}
REQUIRED_LOCAL_ENV = (
    "TEMP",
    "TMP",
    "PIP_CACHE_DIR",
    "TORCH_HOME",
    "HF_HOME",
    "XDG_CACHE_HOME",
    "MPLCONFIGDIR",
    "AUDIO_SEPARATOR_MODEL_DIR",
)

failures: list[str] = []


def result(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def fail(message: str) -> None:
    failures.append(message)
    result("FAIL", message)


def is_within_repo(path: Path) -> bool:
    try:
        return os.path.commonpath((str(REPO_ROOT), str(path.resolve()))) == str(REPO_ROOT)
    except (OSError, ValueError):
        return False


def check_python() -> None:
    actual = sys.version_info[:3]
    if actual == EXPECTED_PYTHON:
        result("PASS", f"Python {'.'.join(map(str, actual))}")
    else:
        fail(
            "Python version mismatch: "
            f"expected {'.'.join(map(str, EXPECTED_PYTHON))}, "
            f"got {'.'.join(map(str, actual))}"
        )

    executable = Path(sys.executable)
    if is_within_repo(executable) and ".venv" in executable.parts:
        result("PASS", f"Python executable is local: {executable}")
    else:
        fail(f"Python executable is not inside the project .venv: {executable}")


def check_local_environment() -> None:
    for name in REQUIRED_LOCAL_ENV:
        raw_value = os.environ.get(name)
        if not raw_value:
            fail(f"{name} is not set")
            continue
        value = Path(raw_value)
        if is_within_repo(value):
            result("PASS", f"{name}={value}")
        else:
            fail(f"{name} escapes the repository: {value}")


def check_nvidia_smi() -> None:
    command = [
        "nvidia-smi",
        "--query-gpu=name,driver_version,memory.total",
        "--format=csv,noheader",
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"nvidia-smi failed: {exc}")
        return
    observed = completed.stdout.strip()
    if EXPECTED_GPU not in observed:
        fail(f"Expected {EXPECTED_GPU}, got: {observed}")
        return
    result("PASS", f"nvidia-smi: {observed}")


def check_torch(profile: str) -> None:
    try:
        import torch
    except Exception as exc:  # diagnostic boundary
        fail(f"Unable to import torch: {exc}")
        return

    accepted = {EXPECTED_TORCH, "2.8.0+cpu"} if profile == "cpu" else {EXPECTED_TORCH}
    if torch.__version__ in accepted:
        result("PASS", f"PyTorch {torch.__version__}")
    else:
        fail(f"PyTorch version mismatch: expected {sorted(accepted)}, got {torch.__version__}")

    result("INFO", f"PyTorch compiled CUDA runtime: {torch.version.cuda}")
    if profile == "cpu":
        try:
            tensor = torch.arange(1, 4097, dtype=torch.float32, device="cpu")
            value = tensor.square().mean().item()
            if tensor.device.type != "cpu" or tensor.dtype != torch.float32:
                raise RuntimeError(
                    f"expected CPU float32 tensor, got {tensor.device}/{tensor.dtype}"
                )
            if not math.isfinite(value):
                raise RuntimeError("CPU tensor result was not finite")
        except Exception as exc:  # diagnostic boundary
            fail(f"CPU tensor smoke failed: {exc}")
            return
        result("PASS", f"CPU FP32 tensor smoke: result={value:.3f}")
        return

    if not torch.cuda.is_available():
        fail("torch.cuda.is_available() returned False")
        return

    try:
        device = torch.cuda.current_device()
        name = torch.cuda.get_device_name(device)
        if name != EXPECTED_GPU:
            raise RuntimeError(f"expected {EXPECTED_GPU}, got {name}")
        capability = torch.cuda.get_device_capability(device)
        total_memory = torch.cuda.get_device_properties(device).total_memory
        tensor = torch.arange(1, 4097, dtype=torch.float32, device="cuda")
        value = (tensor.square().mean()).item()
        torch.cuda.synchronize(device)
        if not math.isfinite(value):
            raise RuntimeError("CUDA tensor result was not finite")
    except Exception as exc:  # diagnostic boundary
        fail(f"CUDA tensor smoke failed: {exc}")
        return

    result(
        "PASS",
        "CUDA tensor smoke: "
        f"device={name}; capability={capability[0]}.{capability[1]}; "
        f"memory={total_memory / (1024**3):.2f} GiB; result={value:.3f}",
    )


def check_audio_separator() -> None:
    try:
        import audio_separator  # noqa: F401

        version = importlib.metadata.version("audio-separator")
    except Exception as exc:  # diagnostic boundary
        fail(f"Unable to import audio-separator: {exc}")
        return

    if version == "0.47.0":
        result("PASS", f"audio-separator {version}")
    else:
        fail(f"audio-separator version mismatch: expected 0.47.0, got {version}")


def check_pyside() -> None:
    try:
        import PySide6
    except Exception as exc:  # diagnostic boundary
        fail(f"Unable to import PySide6: {exc}")
        return
    if PySide6.__version__ == "6.9.2":
        result("PASS", f"PySide6 Essentials {PySide6.__version__}")
    else:
        fail(f"PySide6 version mismatch: expected 6.9.2, got {PySide6.__version__}")


def check_sounddevice() -> None:
    try:
        version = importlib.metadata.version("sounddevice")
        import sounddevice  # noqa: F401
    except Exception as exc:
        fail(f"Unable to import sounddevice: {exc}")
        return
    if version == "0.5.6":
        result("PASS", f"sounddevice {version}")
    else:
        fail(f"sounddevice version mismatch: expected 0.5.6, got {version}")


def check_transformers_and_detector() -> None:
    try:
        version = importlib.metadata.version("transformers")
    except Exception as exc:
        fail(f"Unable to inspect transformers: {exc}")
        return
    if version != "5.18.0":
        fail(f"transformers version mismatch: expected 5.18.0, got {version}")
        return
    result("PASS", f"transformers {version}")
    try:
        from stemlab.instrumentation import verify_detector_artifacts

        receipt = verify_detector_artifacts(
            REPO_ROOT / "models" / "instrument-detector" / "larger_clap_music",
            REPO_ROOT / ".tmp" / "larger-clap-music-install.json",
        )
    except Exception as exc:
        fail(f"Instrument detector verification failed: {exc}")
        return
    result(
        "PASS",
        "Instrument detector verified: "
        f"revision={receipt['source_revision']}; "
        f"weight_sha256={receipt['files']['pytorch_model.bin']['sha256']}",
    )


def check_local_tool(name: str) -> None:
    expected_parent = REPO_ROOT / "tools" / "ffmpeg" / "bin"
    executable_path = expected_parent / f"{name}.exe"
    if not executable_path.is_file() or not is_within_repo(executable_path):
        fail(f"Local {name} is missing from the project: {executable_path}")
        return
    try:
        completed = subprocess.run(
            [str(executable_path), "-version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"{name} version check failed: {exc}")
        return
    first_line = completed.stdout.splitlines()[0]
    if "9.0.2" not in first_line:
        fail(f"Unexpected {name} version: {first_line}")
        return
    result("PASS", f"Local {name}: {first_line} ({executable_path})")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_smoke_model(profile: str) -> None:
    model_dir = REPO_ROOT / "models"
    expected_files = dict(CORE_MODEL_FILES)
    if profile == "gpu":
        expected_files.update(GPU_ONLY_MODEL_FILES)
    for filename, (expected_size, expected_sha256) in expected_files.items():
        path = model_dir / filename
        if not path.is_file():
            fail(f"Smoke model artifact is missing: {path}")
            continue
        size = path.stat().st_size
        if size != expected_size:
            fail(f"Smoke model size mismatch for {filename}: {size} != {expected_size}")
            continue
        actual_sha256 = sha256_file(path)
        if actual_sha256 != expected_sha256:
            fail(f"Smoke model SHA-256 mismatch for {filename}: {actual_sha256}")
            continue
        result("PASS", f"Smoke model artifact verified: {filename} ({size} bytes)")


def check_specialist_candidates() -> None:
    try:
        from stemlab.separation import verify_all_specialist_candidates

        candidates = verify_all_specialist_candidates(REPO_ROOT / "models")
    except Exception as exc:
        fail(f"Specialist candidate verification failed: {exc}")
        return
    for candidate in candidates:
        result(
            "PASS",
            "Research-only specialist verified: "
            f"{candidate.candidate_id}; checkpoint={candidate.checkpoint_sha256}; "
            f"config={candidate.config_sha256}",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stemlab-doctor")
    parser.add_argument("--profile", choices=("gpu", "cpu"), default="gpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    failures.clear()
    args = build_parser().parse_args(argv)
    profile = args.profile
    result("INFO", f"MultiTrack root: {REPO_ROOT}")
    result("INFO", f"Diagnostic profile: {profile}")
    free_bytes = shutil.disk_usage(REPO_ROOT).free
    result("INFO", f"Free disk space: {free_bytes / (1024**3):.2f} GiB")
    check_python()
    check_local_environment()
    if profile == "gpu":
        check_nvidia_smi()
    else:
        result("INFO", "NVIDIA/CUDA checks are not applicable to the CPU profile")
    check_torch(profile)
    check_audio_separator()
    check_pyside()
    check_sounddevice()
    if profile == "gpu":
        check_transformers_and_detector()
    else:
        result("INFO", "CLAP detector is optional and not checked by the CPU profile")
    check_local_tool("ffmpeg")
    check_local_tool("ffprobe")
    check_smoke_model(profile)
    if profile == "gpu":
        check_specialist_candidates()
    else:
        result("INFO", "Research-only specialists are not applicable to the CPU profile")

    if failures:
        result("FAIL", f"Doctor completed with {len(failures)} blocking issue(s)")
        return 1
    result("PASS", "Doctor completed without blocking issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
