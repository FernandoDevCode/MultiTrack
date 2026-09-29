from __future__ import annotations

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
EXPECTED_MODEL_FILES = {
    "model_bs_roformer_ep_317_sdr_12.9755.ckpt": (
        639_331_213,
        "5b84f37e8d444c8cb30c79d77f613a41c05868ff9c9ac6c7049c00aefae115aa",
    ),
    "model_bs_roformer_ep_317_sdr_12.9755.yaml": (
        2_273,
        "2bfdd16c656bd9519aba757cc4f8834b7ede675eb1e00ec4772d74ae1c41af7f",
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


def check_torch() -> None:
    try:
        import torch
    except Exception as exc:  # diagnostic boundary
        fail(f"Unable to import torch: {exc}")
        return

    if torch.__version__ == EXPECTED_TORCH:
        result("PASS", f"PyTorch {torch.__version__}")
    else:
        fail(f"PyTorch version mismatch: expected {EXPECTED_TORCH}, got {torch.__version__}")

    result("INFO", f"PyTorch compiled CUDA runtime: {torch.version.cuda}")
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


def check_smoke_model() -> None:
    model_dir = REPO_ROOT / "models"
    for filename, (expected_size, expected_sha256) in EXPECTED_MODEL_FILES.items():
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


def main() -> int:
    result("INFO", f"StemLab root: {REPO_ROOT}")
    free_bytes = shutil.disk_usage(REPO_ROOT).free
    result("INFO", f"Free disk space: {free_bytes / (1024**3):.2f} GiB")
    check_python()
    check_local_environment()
    check_nvidia_smi()
    check_torch()
    check_audio_separator()
    check_local_tool("ffmpeg")
    check_local_tool("ffprobe")
    check_smoke_model()

    if failures:
        result("FAIL", f"Doctor completed with {len(failures)} blocking issue(s)")
        return 1
    result("PASS", "Doctor completed without blocking issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
