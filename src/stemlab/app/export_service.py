from __future__ import annotations

from pathlib import Path
import shutil

from stemlab.audio import sha256_file


class ExportError(RuntimeError):
    pass


class ExportService:
    def export_one(self, source: Path, destination: Path) -> Path:
        source = source.resolve()
        destination = destination.resolve()
        if not source.is_file():
            raise ExportError(f"Stem não encontrado: {source}")
        if source.suffix.lower() != destination.suffix.lower():
            raise ExportError("A extensão do arquivo exportado deve ser preservada.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with source.open("rb") as reader, destination.open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
        except FileExistsError as exc:
            raise ExportError(f"O destino já existe: {destination}") from exc
        except Exception:
            if destination.exists():
                destination.unlink()
            raise
        if sha256_file(source) != sha256_file(destination):
            destination.unlink(missing_ok=True)
            raise ExportError("A cópia exportada falhou na validação SHA-256.")
        return destination

    def export_all(self, stems: dict[str, Path], destination_dir: Path) -> tuple[Path, ...]:
        destination_dir = destination_dir.resolve()
        if destination_dir.exists():
            raise ExportError(f"A pasta de destino já existe: {destination_dir}")
        destination_dir.mkdir(parents=True)
        exported: list[Path] = []
        try:
            for source in stems.values():
                exported.append(self.export_one(source, destination_dir / source.name))
        except Exception:
            for path in exported:
                path.unlink(missing_ok=True)
            try:
                destination_dir.rmdir()
            except OSError:
                pass
            raise
        return tuple(exported)
