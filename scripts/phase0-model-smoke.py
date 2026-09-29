from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import sys
import time

import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly

from audio_separator.separator import Separator


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_FILENAME = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
MODEL_SHA256 = "5b84f37e8d444c8cb30c79d77f613a41c05868ff9c9ac6c7049c00aefae115aa"
MODEL_BYTES = 639_331_213
YAML_FILENAME = "model_bs_roformer_ep_317_sdr_12.9755.yaml"
YAML_SHA256 = "2bfdd16c656bd9519aba757cc4f8834b7ede675eb1e00ec4772d74ae1c41af7f"
SAMPLE_RATE = 44_100
DURATION_SECONDS = 10.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model(model_dir: Path) -> None:
    checkpoint = model_dir / MODEL_FILENAME
    config = model_dir / YAML_FILENAME
    if checkpoint.stat().st_size != MODEL_BYTES:
        raise RuntimeError("Smoke checkpoint size mismatch")
    if sha256_file(checkpoint) != MODEL_SHA256:
        raise RuntimeError("Smoke checkpoint SHA-256 mismatch")
    if sha256_file(config) != YAML_SHA256:
        raise RuntimeError("Smoke YAML SHA-256 mismatch")


def synthesize_input(path: Path, speech_path: Path | None) -> dict[str, object] | None:
    frame_count = round(SAMPLE_RATE * DURATION_SECONDS)
    t = np.arange(frame_count, dtype=np.float64) / SAMPLE_RATE
    rng = np.random.default_rng(20260929)

    fundamental = 185.0 + 24.0 * np.sin(2.0 * np.pi * 0.19 * t)
    vocal_phase = np.cumsum(2.0 * np.pi * fundamental / SAMPLE_RATE)
    syllable = 0.12 + 0.88 * np.sin(np.pi * np.mod(t * 2.6, 1.0)) ** 2
    phrase = (0.35 + 0.65 * (np.sin(2.0 * np.pi * 0.23 * t) > -0.45)).astype(np.float64)
    vocal = np.zeros_like(t)
    for harmonic in range(1, 9):
        harmonic_frequency = 185.0 * harmonic
        formant_weight = (
            math.exp(-((harmonic_frequency - 740.0) / 430.0) ** 2)
            + 0.65 * math.exp(-((harmonic_frequency - 1_250.0) / 520.0) ** 2)
            + 0.12
        )
        vocal += (formant_weight / harmonic) * np.sin(harmonic * vocal_phase)
    vocal *= 0.13 * syllable * phrase

    chord_left = sum(
        np.sin(2.0 * np.pi * frequency * t + phase)
        for frequency, phase in ((110.0, 0.0), (138.59, 0.4), (164.81, 0.9), (220.0, 0.2))
    )
    chord_right = sum(
        np.sin(2.0 * np.pi * frequency * t + phase)
        for frequency, phase in ((110.0, 0.6), (138.59, 0.1), (164.81, 0.5), (277.18, 1.1))
    )
    chord_envelope = 0.5 + 0.5 * np.sin(2.0 * np.pi * 0.5 * t) ** 2
    chord_left *= 0.055 * chord_envelope
    chord_right *= 0.055 * chord_envelope

    drums = np.zeros_like(t)
    burst_length = round(0.14 * SAMPLE_RATE)
    burst_t = np.arange(burst_length, dtype=np.float64) / SAMPLE_RATE
    for beat_time in np.arange(0.25, DURATION_SECONDS, 0.5):
        start = round(beat_time * SAMPLE_RATE)
        end = min(frame_count, start + burst_length)
        length = end - start
        decay = np.exp(-30.0 * burst_t[:length])
        kick = np.sin(2.0 * np.pi * (75.0 - 25.0 * burst_t[:length]) * burst_t[:length])
        noise = rng.standard_normal(length)
        drums[start:end] += 0.18 * decay * kick + 0.025 * decay * noise

    speech_metadata: dict[str, object] | None = None
    speech = np.zeros(frame_count, dtype=np.float64)
    if speech_path is not None:
        speech_audio, speech_rate = sf.read(
            speech_path, dtype="float32", always_2d=True
        )
        speech_mono = speech_audio.mean(axis=1, dtype=np.float64)
        divisor = math.gcd(speech_rate, SAMPLE_RATE)
        speech_resampled = resample_poly(
            speech_mono, SAMPLE_RATE // divisor, speech_rate // divisor
        )
        speech_peak = float(np.max(np.abs(speech_resampled)))
        if speech_peak <= 0:
            raise RuntimeError(f"Speech fixture is silent: {speech_path}")
        speech_resampled = 0.62 / speech_peak * speech_resampled
        offset = round(0.4 * SAMPLE_RATE)
        copy_length = min(len(speech_resampled), frame_count - offset)
        speech[offset : offset + copy_length] = speech_resampled[:copy_length]
        speech_metadata = {
            "path": str(speech_path),
            "sha256": sha256_file(speech_path),
            "source_sample_rate": speech_rate,
            "source_frames": len(speech_mono),
            "source_duration_seconds": len(speech_mono) / speech_rate,
            "generator": "Windows SAPI local text-to-speech",
        }

    stereo = np.column_stack(
        (
            speech + 0.25 * vocal + chord_left + drums,
            0.97 * np.roll(speech, 7) + 0.25 * np.roll(vocal, 11) + chord_right + 0.94 * drums,
        )
    )
    peak = float(np.max(np.abs(stereo)))
    stereo = (0.82 / peak * stereo).astype(np.float32)
    sf.write(path, stereo, SAMPLE_RATE, subtype="PCM_16")
    return speech_metadata


def resolve_outputs(output_dir: Path, returned: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for item in returned:
        path = Path(item)
        if not path.is_absolute():
            path = output_dir / path
        resolved.append(path.resolve())
    return resolved


def audio_stats(path: Path) -> dict[str, object]:
    info = sf.info(path)
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if sample_rate != SAMPLE_RATE:
        raise RuntimeError(f"Unexpected sample rate for {path}: {sample_rate}")
    if not np.isfinite(audio).all():
        raise RuntimeError(f"NaN/Inf found in {path}")
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    peak = float(np.max(np.abs(audio)))
    if rms <= 1e-4 or peak <= 1e-3:
        raise RuntimeError(f"Silent/empty output: {path} (rms={rms}, peak={peak})")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "frames": info.frames,
        "sample_rate": info.samplerate,
        "channels": info.channels,
        "duration_seconds": info.duration,
        "rms": rms,
        "peak": peak,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--speech-wav",
        type=Path,
        help="Optional locally generated speech WAV to mix into the deterministic fixture.",
    )
    args = parser.parse_args()

    if sys.version_info[:3] != (3, 12, 10):
        raise RuntimeError(f"Expected Python 3.12.10, got {sys.version}")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")

    model_dir = REPO_ROOT / "models"
    verify_model(model_dir)

    # Codex may sanitize workspace PATH entries when starting Python. Restore
    # the already-validated project FFmpeg inside this process so subprocesses
    # created by audio-separator can only resolve the local copy first.
    ffmpeg_bin = REPO_ROOT / "tools" / "ffmpeg" / "bin"
    os.environ["PATH"] = str(ffmpeg_bin) + os.pathsep + os.environ.get("PATH", "")

    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = REPO_ROOT / ".tmp" / "phase0-smoke" / run_id
    output_dir = run_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=False)
    input_path = run_dir / "phase0-synthetic-mix.wav"
    speech_path = args.speech_wav.resolve() if args.speech_wav else None
    if speech_path is not None:
        if not speech_path.is_file():
            raise RuntimeError(f"Speech WAV does not exist: {speech_path}")
        if REPO_ROOT not in speech_path.parents:
            raise RuntimeError(f"Speech WAV must be inside the repository: {speech_path}")
    speech_metadata = synthesize_input(input_path, speech_path)
    input_hash_before = sha256_file(input_path)
    input_info = sf.info(input_path)

    separator = Separator(
        log_level=logging.INFO,
        model_file_dir=str(model_dir),
        output_dir=str(output_dir),
        output_format="WAV",
        normalization_threshold=1.0,
        amplification_threshold=0.0,
        sample_rate=SAMPLE_RATE,
        use_soundfile=True,
        use_autocast=True,
        mdxc_params={
            "segment_size": 256,
            "override_model_segment_size": False,
            "batch_size": 1,
            "overlap": None,
            "pitch_shift": 0,
        },
    )
    if separator.torch_device.type != "cuda":
        raise RuntimeError(f"Separator selected non-CUDA device: {separator.torch_device}")

    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    free_before, total_memory = torch.cuda.mem_get_info()

    total_start = time.perf_counter()
    load_start = time.perf_counter()
    separator.load_model(MODEL_FILENAME)
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - load_start

    model_device = getattr(separator.model_instance, "torch_device", separator.torch_device)
    if model_device.type != "cuda":
        raise RuntimeError(f"Model instance selected non-CUDA device: {model_device}")

    inference_start = time.perf_counter()
    returned_outputs = separator.separate(str(input_path))
    torch.cuda.synchronize()
    inference_seconds = time.perf_counter() - inference_start
    total_seconds = time.perf_counter() - total_start

    peak_allocated = torch.cuda.max_memory_allocated()
    peak_reserved = torch.cuda.max_memory_reserved()
    free_after, _ = torch.cuda.mem_get_info()
    output_paths = resolve_outputs(output_dir, returned_outputs)
    if len(output_paths) != 2:
        raise RuntimeError(f"Expected two stems, got {len(output_paths)}: {output_paths}")

    outputs = [audio_stats(path) for path in output_paths]
    for output in outputs:
        duration_error = abs(float(output["duration_seconds"]) - input_info.duration)
        if duration_error > 0.1:
            raise RuntimeError(
                f"Duration mismatch for {output['path']}: {duration_error:.6f}s"
            )

    input_hash_after = sha256_file(input_path)
    if input_hash_before != input_hash_after:
        raise RuntimeError("Input file changed during separation")

    result = {
        "status": "PASS",
        "run_dir": str(run_dir),
        "input": {
            "path": str(input_path),
            "sha256": input_hash_before,
            "bytes": input_path.stat().st_size,
            "duration_seconds": input_info.duration,
            "sample_rate": input_info.samplerate,
            "channels": input_info.channels,
            "generator": "local TTS plus deterministic harmonics, chords, and percussion",
            "speech_source": speech_metadata,
        },
        "model": {
            "filename": MODEL_FILENAME,
            "sha256": MODEL_SHA256,
            "bytes": MODEL_BYTES,
            "architecture": "BS-RoFormer / audio-separator MDXC",
            "status": "experimental-smoke-only",
        },
        "runtime": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "device": torch.cuda.get_device_name(),
            "device_capability": ".".join(map(str, torch.cuda.get_device_capability())),
            "separator_device": str(separator.torch_device),
            "model_device": str(model_device),
            "effective_precision": separator.effective_precision,
            "load_seconds": load_seconds,
            "inference_seconds": inference_seconds,
            "total_seconds": total_seconds,
            "peak_cuda_allocated_bytes": peak_allocated,
            "peak_cuda_reserved_bytes": peak_reserved,
            "cuda_total_bytes": total_memory,
            "cuda_free_before_bytes": free_before,
            "cuda_free_after_bytes": free_after,
        },
        "outputs": outputs,
        "warnings": [],
    }
    result_path = run_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    latest_path = REPO_ROOT / ".tmp" / "phase0-smoke" / "latest-result.json"
    latest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
