from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stemlab.audio import probe_audio, sha256_file


VIDEO_SUFFIXES = frozenset({".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"})
AUDIO_SUFFIXES = frozenset({".wav", ".flac"})


@dataclass(frozen=True)
class ExtractionRequest:
    input_path: Path
    output_path: Path
    input_sha256: str


def prepare_extraction(input_path: Path, output_path: Path) -> ExtractionRequest:
    source = input_path.resolve()
    target = output_path.resolve()
    if source.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError("Formato de vídeo não suportado.")
    if target.suffix.lower() not in AUDIO_SUFFIXES:
        raise ValueError("A saída deve ser WAV ou FLAC.")
    if not source.is_file():
        raise FileNotFoundError(source)
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    return ExtractionRequest(source, target, sha256_file(source))


def ffmpeg_arguments(request: ExtractionRequest) -> list[str]:
    codec = "pcm_s24le" if request.output_path.suffix.lower() == ".wav" else "flac"
    return [
        "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
        "-i", str(request.input_path), "-map", "0:a:0", "-vn",
        "-c:a", codec, str(request.output_path),
    ]


def validate_extraction(request: ExtractionRequest):
    metadata = probe_audio(request.output_path, validate_finite=True)
    if sha256_file(request.input_path) != request.input_sha256:
        raise RuntimeError("O vídeo de entrada foi modificado durante a extração.")
    return metadata


def monitor_arguments(
    input_path: Path,
    output_path: Path,
    *,
    sample_rate: int,
    channels: int,
) -> list[str]:
    if output_path.suffix.lower() != ".flac":
        raise ValueError("A cópia de monitoramento deve ser FLAC.")
    return [
        "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
        "-i", str(input_path.resolve()), "-map", "0:a:0", "-vn",
        "-c:a", "flac", "-ar", str(sample_rate), "-ac", str(channels),
        str(output_path.resolve()),
    ]
