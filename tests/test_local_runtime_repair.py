from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _repair_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "repair-local-runtime.py"
    spec = importlib.util.spec_from_file_location("repair_local_runtime", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _moved_runtime(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "Música & projeto movido"
    for relative in (
        "tools/python312/python.exe", "tools/python312/pythonw.exe",
        ".venv/Scripts/python.exe", ".venv/Scripts/pythonw.exe",
        "src/stemlab/__init__.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    config = root / ".venv/pyvenv.cfg"
    config.write_text(
        "home = G:\\multiTrack\\tools\\python312\n"
        "include-system-site-packages = false\nversion = 3.12.10\n"
        "executable = G:\\multiTrack\\tools\\python312\\python.exe\n"
        "command = old command\n", encoding="utf-8",
    )
    editable = root / ".venv/Lib/site-packages/__editable__.stemlab-0.1.0.pth"
    editable.parent.mkdir(parents=True)
    editable.write_text("G:\\multiTrack\\src\n", encoding="utf-8")
    return root, config, editable


def test_repair_after_drive_change_preserves_packages_and_is_idempotent(tmp_path: Path):
    root, config, editable = _moved_runtime(tmp_path)
    package = editable.parent / "installed-package.bin"
    package.write_bytes(b"keep existing dependencies")
    repair = _repair_module().repair_runtime

    assert set(repair(root)) == {config, editable}

    assert f"home = {root / 'tools/python312'}" in config.read_text(encoding="utf-8")
    assert "G:\\multiTrack" not in config.read_text(encoding="utf-8")
    assert "version = 3.12.10" in config.read_text(encoding="utf-8")
    assert "include-system-site-packages = false" in config.read_text(encoding="utf-8")
    assert editable.read_text(encoding="utf-8").strip() == str(root / "src")
    assert package.read_bytes() == b"keep existing dependencies"
    mtimes = (config.stat().st_mtime_ns, editable.stat().st_mtime_ns)
    assert repair(root) == []
    assert mtimes == (config.stat().st_mtime_ns, editable.stat().st_mtime_ns)


def test_incomplete_runtime_fails_before_changing_paths(tmp_path: Path):
    root, config, editable = _moved_runtime(tmp_path)
    before = (config.read_bytes(), editable.read_bytes())
    (root / "tools/python312/python.exe").unlink()

    with pytest.raises(FileNotFoundError):
        _repair_module().repair_runtime(root)

    assert before == (config.read_bytes(), editable.read_bytes())


def test_unexpected_editable_format_is_not_overwritten(tmp_path: Path):
    root, config, editable = _moved_runtime(tmp_path)
    editable.write_text("import custom_finder\n", encoding="utf-8")
    before = (config.read_bytes(), editable.read_bytes())

    with pytest.raises(RuntimeError, match="Unsupported"):
        _repair_module().repair_runtime(root)

    assert before == (config.read_bytes(), editable.read_bytes())
