"""Local-only CPU setup, invoked by the Windows bootstrap's verified Python.

No global Python, driver, CUDA Toolkit, package manager or PATH changes.
All network artifacts are verified before use. No source builds on the target.
"""
from __future__ import annotations

import hashlib
from contextlib import redirect_stderr, redirect_stdout
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {"api.nuget.org", "files.pythonhosted.org", "download-r2.pytorch.org", "www.gyan.dev"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_artifact(artifact: dict) -> None:
    name = artifact["filename"]
    url = urlparse(artifact["url"])
    if (
        not isinstance(name, str) or Path(name).name != name
        or "/" in name or "\\" in name or ":" in name or name in {"", ".", ".."}
        or url.scheme != "https" or url.hostname not in HOSTS
        or url.username or url.password or url.port is not None
        or type(artifact["bytes"]) is not int or artifact["bytes"] <= 0
        or len(artifact["sha256"]) != 64
        or any(c not in "0123456789abcdef" for c in artifact["sha256"])
    ):
        raise ValueError("Invalid or unapproved setup artifact")


def verified(path: Path, artifact: dict) -> bool:
    return path.is_file() and path.stat().st_size == artifact["bytes"] and digest(path) == artifact["sha256"]


def download(artifact: dict, folder: Path, *, opener=urllib.request.urlopen) -> Path:
    validate_artifact(artifact)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / artifact["filename"]
    if verified(destination, artifact):
        print(f"Cache verificado: {destination.name}", flush=True)
        return destination
    if destination.exists():
        raise RuntimeError(f"Cache corrompido: {destination}. Remova somente esse arquivo e tente novamente.")
    partial = destination.with_name(destination.name + ".partial")
    # Restart incomplete untrusted data. Never publish it until hash + size pass.
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(artifact["url"], headers={"User-Agent": "MultiTrack-CPU-Setup/1"})
            with opener(request, timeout=60) as response, partial.open("wb") as stream:
                count = 0
                reported = time.monotonic()
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > artifact["bytes"]:
                        raise ValueError(f"Download excedeu o tamanho aprovado: {destination.name}")
                    stream.write(chunk)
                    if time.monotonic() - reported >= 2:
                        print(f"  {destination.name}: {count * 100 // artifact['bytes']}%", flush=True)
                        reported = time.monotonic()
            break
        except (OSError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError(f"Download falhou: {destination.name}. Confira a internet e tente novamente.") from exc
            print(f"Tentando novamente ({attempt}/3): {destination.name}", flush=True)
    if not verified(partial, artifact):
        raise ValueError(f"SHA-256/tamanho invalido: {destination.name}. Nada desse download foi instalado.")
    partial.replace(destination)
    return destination


def extract_zip(archive: Path, destination: Path) -> list[str]:
    """Validate all entries before extraction, including Windows path aliases."""
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        for name in names:
            parts = PurePosixPath(name.replace("\\", "/")).parts
            if (
                name.startswith(("/", "\\")) or ".." in parts
                or any(":" in part or part.endswith((".", " ")) for part in parts)
                or not (destination / name).resolve().is_relative_to(destination.resolve())
            ):
                raise ValueError("Unsafe path in setup archive")
            mode = zipped.getinfo(name).external_attr >> 16
            if mode & 0o170000 == 0o120000:
                raise ValueError("Symbolic links are not allowed in setup archives")
        zipped.extractall(destination)
    return names


def local_environment(root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    for key, relative in {
        "TEMP": ".tmp", "TMP": ".tmp", "PIP_CACHE_DIR": ".cache/pip",
        "TORCH_HOME": ".cache/torch", "HF_HOME": ".cache/huggingface",
        "XDG_CACHE_HOME": ".cache", "MPLCONFIGDIR": ".cache/matplotlib",
        "AUDIO_SEPARATOR_MODEL_DIR": "models",
    }.items():
        path = root / relative
        path.mkdir(parents=True, exist_ok=True)
        environment[key] = str(path)
    environment.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", CUDA_VISIBLE_DEVICES="-1")
    environment["PATH"] = os.pathsep.join((str(root / "tools/ffmpeg/bin"), str(root / ".venv/Scripts"), environment.get("PATH", "")))
    return environment


def install_local_msvc(root: Path, wheel: Path, pin: dict) -> dict[str, str]:
    """Supply Torch's local Library/bin search path from the verified Qt wheel.

    Preserve upstream DLLs and their licenses; no redist installer/system write.
    Read from the pinned wheel rather than trusting an existing installation.
    """
    if not verified(wheel, pin):
        raise ValueError("PySide runtime wheel integrity failed")
    folder = root / ".venv/Library/bin"
    folder.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with zipfile.ZipFile(wheel) as package:
        for name in (
            "concrt140.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
            "msvcp140_codecvt_ids.dll", "vcruntime140.dll", "vcruntime140_1.dll",
        ):
            data = package.read("PySide6/" + name)
            hashes[name] = hashlib.sha256(data).hexdigest()
            destination = folder / name
            if destination.is_file() and digest(destination) == hashes[name]:
                continue
            partial = destination.with_suffix(".dll.partial")
            partial.write_bytes(data)
            partial.replace(destination)
    return hashes


def run(arguments: list[str], root: Path, environment: dict[str, str]) -> None:
    # The entry point tees every stage and child output to the local setup log.
    process = subprocess.Popen(
        arguments, cwd=root, env=environment, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
    if process.wait() != 0:
        raise RuntimeError("Uma etapa falhou. Veja .tmp/install-cpu.log; o instalador pode ser executado novamente.")


def install(root: Path = ROOT) -> None:
    root = root.resolve()
    environment = local_environment(root)
    setup_temp = root / ".tmp/cpu-setup"
    setup_temp.mkdir(parents=True, exist_ok=True)
    marker = setup_temp / "in-progress.json"
    receipt = root / ".tmp/cpu-install-receipt.json"
    python = root / "tools/python312/python.exe"
    venv_python = root / ".venv/Scripts/python.exe"
    if sys.version_info[:3] != (3, 12, 10):
        raise RuntimeError("Use o Python local 3.12.10 fornecido pelo bootstrap.")
    if (root / ".venv").exists() and not marker.is_file() and not receipt.is_file():
        raise RuntimeError("Ambiente existente nao sera convertido. Extraia o pacote CPU em outra pasta.")
    if shutil.disk_usage(root).free < 6 * 1024**3:
        raise RuntimeError("Libere pelo menos 6 GiB nesta unidade para instalar e processar audio.")
    manifest = json.loads((root / "resources/cpu-setup.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != 1 or manifest["profile"] != "cpu":
        raise ValueError("Unsupported setup manifest")
    wheels = manifest["wheels"]
    for artifact in (manifest["python"], manifest["ffmpeg"], *wheels):
        validate_artifact(artifact)
    names = [wheel["name"].lower() for wheel in wheels]
    if len(names) != len(set(names)) or "onnxruntime-gpu" in names:
        raise ValueError("Invalid CPU dependency set")
    plan_hash = digest(root / "resources/cpu-setup.json")
    previous = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
    successful = json.loads(receipt.read_text(encoding="utf-8")) if receipt.is_file() else {}
    had_venv = (root / ".venv").exists()
    dependencies_ready = (
        successful.get("manifest_sha256") == plan_hash
        or previous.get("manifest_sha256") == plan_hash and previous.get("dependencies_complete") is True
    )
    state = {"profile": "cpu", "manifest_sha256": plan_hash, "dependencies_complete": dependencies_ready}

    def save_state() -> None:
        temporary = marker.with_suffix(".partial")
        temporary.write_text(json.dumps(state), encoding="utf-8")
        temporary.replace(marker)

    save_state()
    print("[2/6] Preparando FFmpeg local...", flush=True)
    ffmpeg = root / "tools/ffmpeg"
    if not ffmpeg.exists():
        archive = download(manifest["ffmpeg"], setup_temp)
        staging = Path(tempfile.mkdtemp(prefix="ffmpeg-", dir=setup_temp))
        entries = extract_zip(archive, staging)
        top_levels = {PurePosixPath(name).parts[0] for name in entries}
        if len(top_levels) != 1:
            raise ValueError("Unexpected FFmpeg archive layout")
        unpacked = staging / top_levels.pop()
        for binary in ("ffmpeg.exe", "ffprobe.exe"):
            if not (unpacked / "bin" / binary).is_file():
                raise ValueError("FFmpeg archive is incomplete")
        unpacked.replace(ffmpeg)
    print("[3/6] Baixando dependencias CPU verificadas (sem CUDA)...", flush=True)
    wheel_folder = root / ".cache/cpu-wheels"
    for index, wheel in enumerate(wheels, 1):
        print(f"  [{index}/{len(wheels)}] {wheel['name']} {wheel['version']}", flush=True)
        download(wheel, wheel_folder)
    print("[4/6] Instalando o ambiente local...", flush=True)
    if not venv_python.is_file():
        run([str(python), "-I", "-m", "venv", str(root / ".venv")], root, environment)
    pip = [str(venv_python), "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--cache-dir", str(root / ".cache/pip")]
    repair_flags = ["--force-reinstall"] if had_venv and not dependencies_ready else []
    run([*pip, "install", "--no-input", "--no-compile", *repair_flags, "--only-binary=:all:", "--no-index", "--find-links", str(wheel_folder), "--require-hashes", "-r", str(root / "requirements-cpu.txt")], root, environment)
    state["dependencies_complete"] = True
    save_state()
    pyside_pin = next(pin for pin in wheels if pin["name"].lower() == "pyside6-essentials")
    msvc = install_local_msvc(root, wheel_folder / pyside_pin["filename"], pyside_pin)
    run([*pip, "install", "--no-input", "--no-compile", "--no-index", "--no-deps", "--no-build-isolation", "-e", str(root) + "[cpu]"], root, environment)
    run([str(python), "-I", str(root / "scripts/repair-local-runtime.py")], root, environment)
    print("[5/6] Instalando/verificando modelo Core aprovado...", flush=True)
    model_script = root / "scripts/install_bs_roformer_sw.py"
    model_args = [str(venv_python), "-I", "-X", "utf8", str(model_script)]
    if all((root / "models" / filename).is_file() for filename in ("BS-Roformer-SW.ckpt", "BS-Roformer-SW.yaml")):
        model_args.append("--verify-only")
    run(model_args, root, environment)
    print("[6/6] Verificando instalacao CPU e interface...", flush=True)
    run([*pip, "check"], root, environment)
    run([str(venv_python), "-I", str(root / "scripts/doctor.py"), "--profile", "cpu"], root, environment)
    run([str(venv_python), "-I", "-c", "import torch; from stemlab.ui import MainWindow; assert torch.__version__ == '2.8.0+cpu'; assert torch.version.cuda is None; assert not torch.cuda.is_available(); print('Runtime CPU e interface: OK')"], root, environment)
    data = {
        "profile": "cpu", "torch": "2.8.0+cpu", "python": "3.12.10",
        "manifest_sha256": digest(root / "resources/cpu-setup.json"),
        "local_msvc_dll_sha256": msvc,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    partial_receipt = receipt.with_suffix(".partial")
    partial_receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    partial_receipt.replace(receipt)
    marker.unlink(missing_ok=True)
    print("Instalacao CPU concluida. O app funciona offline apos este setup.", flush=True)


class SetupOutput:
    def __init__(self, console, log):
        self.console = console
        self.log = log

    def write(self, text: str) -> int:
        self.console.write(text)
        self.log.write(text)
        return len(text)

    def flush(self) -> None:
        self.console.flush()
        self.log.flush()


if __name__ == "__main__":
    (ROOT / ".tmp").mkdir(exist_ok=True)
    with (ROOT / ".tmp/install-cpu.log").open("a", encoding="utf-8", buffering=1) as log:
        with redirect_stdout(SetupOutput(sys.stdout, log)), redirect_stderr(SetupOutput(sys.stderr, log)):
            try:
                install()
            except Exception as exc:
                print(f"ERRO: {exc}", file=sys.stderr)
                raise SystemExit(1)
