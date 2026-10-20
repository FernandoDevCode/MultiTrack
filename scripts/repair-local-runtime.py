"""Repair the two absolute paths used by our existing local Windows runtime.

Run with tools/python312/python.exe, since a moved .venv cannot start yet.
This preserves all installed packages and never downloads or installs anything.
"""
from __future__ import annotations

from pathlib import Path
import sys


def repair_runtime(repo_root: Path) -> list[Path]:
    root = repo_root.resolve()
    base = root / "tools" / "python312"
    venv = root / ".venv"
    config = venv / "pyvenv.cfg"
    site_packages = venv / "Lib" / "site-packages"
    editable_paths = list(site_packages.glob("__editable__.stemlab-*.pth"))
    required = [base / "python.exe", base / "pythonw.exe", config,
                venv / "Scripts" / "python.exe", venv / "Scripts" / "pythonw.exe",
                root / "src" / "stemlab" / "__init__.py"]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"Local runtime file missing: {path}")
    if len(editable_paths) != 1:
        raise RuntimeError("Expected exactly one local MultiTrack editable installation")
    editable = editable_paths[0]
    # Our pinned setuptools installation uses a plain source path, not a finder.
    # Refuse an unexpected format rather than replacing executable .pth code.
    editable_text = editable.read_text(encoding="utf-8").strip()
    if not editable_text or "\n" in editable_text or editable_text.startswith("import "):
        raise RuntimeError(f"Unsupported MultiTrack editable path format: {editable}")

    replacements = {
        "home": str(base),
        "executable": str(base / "python.exe"),
        "command": f'{base / "python.exe"} -m venv {venv}',
    }
    lines = config.read_text(encoding="utf-8").splitlines()
    updated = []
    for line in lines:
        key, separator, _value = line.partition("=")
        name = key.strip()
        if separator and name in replacements:
            updated.append(f"{name} = {replacements.pop(name)}")
        else:
            updated.append(line)
    updated.extend(f"{key} = {value}" for key, value in replacements.items())
    changes = {config: "\n".join(updated) + "\n", editable: str(root / "src") + "\n"}
    changed = []
    for path, content in changes.items():
        if path.read_text(encoding="utf-8") != content:
            partial = path.with_name(path.name + ".partial")
            partial.write_text(content, encoding="utf-8", newline="\n")
            partial.replace(path)
            changed.append(path)
    return changed


def main() -> int:
    try:
        for path in repair_runtime(Path(__file__).resolve().parents[1]):
            print(f"Updated local runtime path: {path}")
    except (OSError, RuntimeError) as exc:
        print(f"MultiTrack runtime repair failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
