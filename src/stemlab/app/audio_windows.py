from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

import numpy as np

from stemlab.domain import AnalysisWindow


SAMPLE_RATE = 48_000
WINDOW_SECONDS = 10.0
MAX_WINDOWS = 8


def plan_analysis_windows(duration_seconds: float) -> tuple[AnalysisWindow, ...]:
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("Audio duration must be positive and finite.")
    if duration_seconds <= WINDOW_SECONDS:
        return (AnalysisWindow(0, 0.0, round(duration_seconds, 6)),)
    count = min(MAX_WINDOWS, max(2, math.ceil(duration_seconds / WINDOW_SECONDS)))
    last_start = duration_seconds - WINDOW_SECONDS
    return tuple(
        AnalysisWindow(
            index=index,
            start_seconds=round(last_start * index / (count - 1), 6),
            duration_seconds=WINDOW_SECONDS,
        )
        for index in range(count)
    )


class FfmpegWindowDecoder:
    def __init__(self, ffmpeg_bin: Path) -> None:
        self.ffmpeg = ffmpeg_bin.resolve() / "ffmpeg.exe"
        self.ffprobe = ffmpeg_bin.resolve() / "ffprobe.exe"
        if not self.ffmpeg.is_file() or not self.ffprobe.is_file():
            raise FileNotFoundError("Local FFmpeg/FFprobe executables are required.")

    def duration_seconds(self, input_path: Path) -> float:
        completed = subprocess.run(
            [
                str(self.ffprobe),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(input_path.resolve()),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=30,
        )
        payload = json.loads(completed.stdout)
        return float(payload["format"]["duration"])

    def decode(self, input_path: Path, window: AnalysisWindow) -> np.ndarray:
        completed = subprocess.run(
            [
                str(self.ffmpeg),
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{window.start_seconds:.6f}",
                "-t",
                f"{window.duration_seconds:.6f}",
                "-i",
                str(input_path.resolve()),
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(SAMPLE_RATE),
                "-f",
                "f32le",
                "pipe:1",
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        samples = np.frombuffer(completed.stdout, dtype="<f4").copy()
        if samples.size == 0 or not np.isfinite(samples).all():
            raise RuntimeError(f"FFmpeg returned invalid samples for window {window.index}.")
        return samples
