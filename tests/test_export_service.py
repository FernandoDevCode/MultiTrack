from __future__ import annotations

from pathlib import Path

import pytest

from stemlab.app.export_service import ExportError, ExportService
from stemlab.audio import sha256_file


def test_export_one_is_byte_identical_and_never_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "stem.flac"
    source.write_bytes(bytes(range(256)) * 20)
    destination = tmp_path / "delivery" / "stem.flac"
    service = ExportService()
    assert service.export_one(source, destination) == destination.resolve()
    assert sha256_file(source) == sha256_file(destination)
    with pytest.raises(ExportError, match="já existe"):
        service.export_one(source, destination)


def test_export_all_preserves_every_file_and_rejects_folder_collision(tmp_path: Path) -> None:
    stems = {}
    for index, role in enumerate(("vocals", "drums", "bass")):
        path = tmp_path / f"{role}.wav"
        path.write_bytes(bytes([index + 1]) * (100 + index))
        stems[role] = path
    destination = tmp_path / "all-export"
    exported = ExportService().export_all(stems, destination)
    assert {path.name for path in exported} == {path.name for path in stems.values()}
    for source in stems.values():
        assert sha256_file(source) == sha256_file(destination / source.name)
    with pytest.raises(ExportError, match="já existe"):
        ExportService().export_all(stems, destination)


def test_export_preserves_extension(tmp_path: Path) -> None:
    source = tmp_path / "stem.wav"
    source.write_bytes(b"pcm")
    with pytest.raises(ExportError, match="extensão"):
        ExportService().export_one(source, tmp_path / "stem.flac")
