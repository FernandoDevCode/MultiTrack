from __future__ import annotations

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def artifact(data=b"trusted fixture"):
    return {"filename": "fixture.whl", "url": "https://files.pythonhosted.org/fixture.whl",
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def test_setup_download_checks_hash_before_publishing_and_reuses_cache(tmp_path):
    installer = module("install_cpu")
    pin = artifact()
    path = installer.download(pin, tmp_path, opener=lambda *a, **kw: io.BytesIO(b"trusted fixture"))
    assert path.read_bytes() == b"trusted fixture"
    assert not path.with_suffix(".whl.partial").exists()

    def no_network(*args, **kwargs):
        raise AssertionError("cache hit used network")

    assert installer.download(pin, tmp_path, opener=no_network) == path
    path.write_bytes(b"corrupt")
    with pytest.raises(RuntimeError, match="Cache corrompido"):
        installer.download(pin, tmp_path, opener=no_network)
    assert path.read_bytes() == b"corrupt"


@pytest.mark.parametrize("bad_data", [b"bad", b"untrusted data!", b"longer than the approved size"])
def test_corrupt_or_truncated_download_is_never_published(tmp_path, bad_data):
    with pytest.raises(ValueError):
        module("install_cpu").download(artifact(), tmp_path, opener=lambda *a, **kw: io.BytesIO(bad_data))
    assert not (tmp_path / "fixture.whl").exists()


def test_download_restarts_partial_after_connection_failure(tmp_path):
    calls = []
    (tmp_path / "fixture.whl.partial").write_bytes(b"old partial")

    def flaky(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("interrupted")
        return io.BytesIO(b"trusted fixture")

    path = module("install_cpu").download(artifact(), tmp_path, opener=flaky)
    assert path.read_bytes() == b"trusted fixture"
    assert len(calls) == 2


@pytest.mark.parametrize("change", [
    {"url": "http://files.pythonhosted.org/fixture.whl"},
    {"url": "https://unapproved.example/fixture.whl"},
    {"filename": "../outside.whl"}, {"filename": "C:\\outside.whl"},
    {"filename": "fixture.whl:stream"}, {"sha256": "invalid"}, {"bytes": -1},
])
def test_invalid_or_unapproved_artifact_fails_before_download(tmp_path, change):
    pin = artifact()
    pin.update(change)
    with pytest.raises(ValueError):
        module("install_cpu").download(pin, tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", ["../escape", "/absolute", "C:/escape", "safe/../../escape", "safe\\..\\escape", "safe/file:stream", "safe./escape"])
def test_archive_paths_cannot_escape_or_alias_installation_root(tmp_path, name):
    archive = tmp_path / "test.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("safe/valid.txt", b"valid")
        zipped.writestr(name, b"invalid")
    destination = tmp_path / "unpacked"
    destination.mkdir()
    with pytest.raises(ValueError, match="Unsafe path"):
        module("install_cpu").extract_zip(archive, destination)
    assert list(destination.iterdir()) == []


def test_cpu_manifest_and_hash_lock_match_exactly():
    manifest = json.loads((ROOT / "resources/cpu-setup.json").read_text())
    wheels = manifest["wheels"]
    installer = module("install_cpu")
    for pin in [manifest["python"], manifest["ffmpeg"], *wheels]:
        installer.validate_artifact(pin)
    expected = {f"{pin['name']}=={pin['version']} --hash=sha256:{pin['sha256']}" for pin in wheels}
    actual = {line for line in (ROOT / "requirements-cpu.txt").read_text().splitlines() if line and not line.startswith("#")}
    assert expected == actual
    assert len(wheels) == len({pin["name"] for pin in wheels})
    assert next(pin for pin in wheels if pin["name"] == "torch")["version"] == "2.8.0+cpu"
    assert "onnxruntime-gpu" not in {pin["name"] for pin in wheels}
    assert all(pin["filename"].endswith(".whl") for pin in wheels)


def test_local_msvc_is_copied_only_from_verified_wheel_and_is_repeatable(tmp_path):
    installer = module("install_cpu")
    wheel = tmp_path / "runtime.whl"
    names = ["concrt140.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "msvcp140_codecvt_ids.dll", "vcruntime140.dll", "vcruntime140_1.dll"]
    with zipfile.ZipFile(wheel, "w") as package:
        for name in names:
            package.writestr("PySide6/" + name, b"verified fixture " + name.encode())
    pin = artifact(wheel.read_bytes())
    hashes = installer.install_local_msvc(tmp_path, wheel, pin)
    assert set(hashes) == set(names)
    paths = [tmp_path / ".venv/Library/bin" / name for name in names]
    mtimes = [path.stat().st_mtime_ns for path in paths]
    assert installer.install_local_msvc(tmp_path, wheel, pin) == hashes
    assert mtimes == [path.stat().st_mtime_ns for path in paths]
    wheel.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        installer.install_local_msvc(tmp_path, wheel, pin)


def test_cpu_package_contains_only_allowlisted_sources_and_integrity_manifest(tmp_path):
    package_path = tmp_path / "MultiTrack-CPU.zip"
    report = module("build_cpu_package").build(ROOT, package_path)
    assert report["sha256"] == hashlib.sha256(package_path.read_bytes()).hexdigest()
    with zipfile.ZipFile(package_path) as package:
        manifest = json.loads(package.read("MultiTrack-CPU/package-manifest.json"))
        for name, expected in manifest["files"].items():
            assert hashlib.sha256(package.read("MultiTrack-CPU/" + name)).hexdigest() == expected
        names = {name.removeprefix("MultiTrack-CPU/") for name in package.namelist()}
        assert {"INSTALAR-CPU.bat", "START-MULTITRACK.bat", "resources/cpu-setup.json", "scripts/install_cpu.py"} <= names
        assert not any(name.startswith((".venv/", "tools/", "models/", "outputs/", ".cache/", ".tmp/", ".git/")) for name in names)
        assert not any(name.endswith((".wav", ".mp3", ".ckpt", ".pth", ".env")) for name in names)
