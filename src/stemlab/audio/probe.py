from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import soundfile as sf

from stemlab.domain import AudioMetadata, OutputValidationError


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_audio(path: Path, *, validate_finite: bool = False) -> AudioMetadata:
    resolved = path.resolve()
    try:
        info = sf.info(resolved)
    except (OSError, RuntimeError) as exc:
        raise OutputValidationError(
            f"Audio file cannot be opened: {resolved}",
            details={"path": str(resolved), "reason": str(exc)},
        ) from exc

    if info.frames <= 0 or info.samplerate <= 0 or info.channels <= 0:
        raise OutputValidationError(
            f"Audio file has invalid dimensions: {resolved}",
            details={
                "frames": info.frames,
                "sample_rate": info.samplerate,
                "channels": info.channels,
            },
        )

    if validate_finite:
        try:
            for block in sf.blocks(resolved, blocksize=65_536, dtype="float32", always_2d=True):
                if not np.isfinite(block).all():
                    raise OutputValidationError(
                        f"Audio file contains NaN or Inf samples: {resolved}",
                        details={"path": str(resolved)},
                    )
        except OutputValidationError:
            raise
        except (OSError, RuntimeError) as exc:
            raise OutputValidationError(
                f"Audio samples cannot be read: {resolved}",
                details={"path": str(resolved), "reason": str(exc)},
            ) from exc

    return AudioMetadata(
        path=resolved,
        format=info.format,
        subtype=info.subtype,
        frames=info.frames,
        duration_seconds=info.duration,
        sample_rate=info.samplerate,
        channels=info.channels,
        bytes=resolved.stat().st_size,
        sha256=sha256_file(resolved),
    )


def audio_signal_stats(path: Path) -> tuple[float, float]:
    square_sum = 0.0
    sample_count = 0
    peak = 0.0
    try:
        for block in sf.blocks(path, blocksize=65_536, dtype="float32", always_2d=True):
            if not np.isfinite(block).all():
                raise OutputValidationError(
                    f"Audio file contains NaN or Inf samples: {path}",
                    details={"path": str(path)},
                )
            values = block.astype(np.float64, copy=False)
            square_sum += float(np.square(values).sum())
            sample_count += values.size
            peak = max(peak, float(np.max(np.abs(values))))
    except OutputValidationError:
        raise
    except (OSError, RuntimeError) as exc:
        raise OutputValidationError(
            f"Audio samples cannot be read: {path}",
            details={"path": str(path), "reason": str(exc)},
        ) from exc
    rms = float(np.sqrt(square_sum / sample_count)) if sample_count else 0.0
    return rms, peak
