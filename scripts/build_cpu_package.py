"""Build the small online CPU setup ZIP from an explicit source allowlist."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    "INSTALAR-CPU.bat", "START-MULTITRACK.bat", "START-STEMLAB.bat",
    "LEIA-ME-CPU.txt", "README.md", "README-FIRST.md", "pyproject.toml",
    "requirements-cpu.txt", "resources/cpu-setup.json",
    "docs/16_COLLABORATOR_SETUP.md", "docs/17_CPU_INSTALLER.md",
)
SCRIPTS = (
    "install-cpu.ps1", "install_cpu.py", "repair-local-runtime.py",
    "create-shortcut.ps1", "doctor.py", "dev-env.ps1", "install_bs_roformer_sw.py",
)


def build(root: Path, destination: Path) -> dict:
    root = root.resolve()
    files = [root / name for name in ROOT_FILES]
    files.extend(root / "scripts" / name for name in SCRIPTS)
    files.extend(path for path in (root / "src/stemlab").rglob("*.py") if "__pycache__" not in path.parts)
    files.extend(path for path in (root / "resources/icons").iterdir() if path.suffix in {".svg", ".ico", ".png"})
    files.sort()
    for path in files:
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Missing or unsafe package source: {path}")
    content = {path.relative_to(root).as_posix(): path.read_bytes() for path in files}
    manifest = {
        "profile": "cpu", "format_version": 1,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in content.items()},
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(".zip.partial")
    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in content.items():
            package.writestr("MultiTrack-CPU/" + name, data)
        package.writestr("MultiTrack-CPU/package-manifest.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(partial) as package:
        if package.testzip() is not None:
            raise ValueError("Package CRC verification failed")
    partial.replace(destination)
    sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(f"{sha256}  {destination.name}\n", encoding="ascii")
    return {"path": str(destination.resolve()), "files": len(content), "bytes": destination.stat().st_size, "sha256": sha256}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/packages/MultiTrack-CPU-setup.zip")
    args = parser.parse_args()
    print(json.dumps(build(ROOT, args.output), indent=2))
