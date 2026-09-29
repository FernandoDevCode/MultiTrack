from __future__ import annotations

from contextlib import contextmanager
import logging
import os
from pathlib import Path
import re
import time
from typing import Iterator

import torch
from audio_separator.separator import Separator

from stemlab.domain import (
    AudioMetadata,
    BackendSeparationError,
    DevicePolicy,
    DeviceUnavailableError,
    SeparationRequest,
)
from stemlab.separation.backend import BackendResult, BackendStem


_ROLE_RE = re.compile(r"_\(([^)]+)\)_")


class AudioSeparatorBackend:
    """The only StemLab module coupled to the audio-separator package."""

    backend_id = "audio-separator/0.47.0"

    def __init__(self, *, models_dir: Path, ffmpeg_bin: Path | None = None) -> None:
        self.models_dir = models_dir.resolve()
        self.ffmpeg_bin = ffmpeg_bin.resolve() if ffmpeg_bin else None

    def separate(
        self, request: SeparationRequest, input_metadata: AudioMetadata
    ) -> BackendResult:
        model_paths = (request.model.checkpoint_path, *request.model.config_paths)
        if any(
            self.models_dir not in path.resolve().parents
            for path in model_paths
        ):
            raise BackendSeparationError(
                "Model artifacts must be located inside the configured models directory.",
                details={"models_dir": str(self.models_dir)},
            )
        if request.device_policy is DevicePolicy.CUDA_REQUIRED and not torch.cuda.is_available():
            raise DeviceUnavailableError(
                "CUDA was required but is not available.",
                details={"requested_policy": request.device_policy.value},
            )

        output_dir = request.output_dir.resolve()
        separator_kwargs = {
            "log_level": logging.INFO,
            "model_file_dir": str(self.models_dir),
            "output_dir": str(output_dir),
            "output_format": request.output_format.value,
            "normalization_threshold": 1.0,
            "amplification_threshold": 0.0,
            "sample_rate": input_metadata.sample_rate,
            "use_soundfile": True,
            "use_autocast": request.use_autocast,
            "mdxc_params": {
                "segment_size": 256,
                "override_model_segment_size": False,
                "batch_size": 1,
                "overlap": None,
                "pitch_shift": 0,
            },
        }

        try:
            with self._project_environment():
                separator = Separator(**separator_kwargs)
                selected_device = separator.torch_device.type
                if request.device_policy is DevicePolicy.CUDA_REQUIRED and selected_device != "cuda":
                    raise DeviceUnavailableError(
                        "audio-separator selected a non-CUDA device while CUDA was required.",
                        details={"selected_device": str(separator.torch_device)},
                    )

                if selected_device == "cuda":
                    torch.cuda.empty_cache()
                    torch.cuda.reset_peak_memory_stats()

                total_start = time.perf_counter()
                load_start = time.perf_counter()
                separator.load_model(request.model.checkpoint_path.name)
                self._synchronize(selected_device)
                load_seconds = time.perf_counter() - load_start

                model_device = getattr(
                    separator.model_instance, "torch_device", separator.torch_device
                )
                effective_device = model_device.type
                if request.device_policy is DevicePolicy.CUDA_REQUIRED and effective_device != "cuda":
                    raise DeviceUnavailableError(
                        "Loaded model is not on CUDA while CUDA was required.",
                        details={"model_device": str(model_device)},
                    )

                inference_start = time.perf_counter()
                returned = separator.separate(str(request.input_path.resolve()))
                self._synchronize(effective_device)
                inference_seconds = time.perf_counter() - inference_start
                total_seconds = time.perf_counter() - total_start

                stems = tuple(
                    BackendStem(role=self._role_for(path), path=path)
                    for path in self._resolve_outputs(output_dir, returned)
                )
                warnings: tuple[str, ...] = ()
                if effective_device != "cuda":
                    warnings = (
                        "Device policy 'auto' selected CPU; this was explicit, not a silent fallback.",
                    )
                return BackendResult(
                    backend_id=self.backend_id,
                    effective_device=effective_device,
                    effective_precision=getattr(separator, "effective_precision", None),
                    model_load_seconds=load_seconds,
                    inference_seconds=inference_seconds,
                    total_seconds=total_seconds,
                    stems=stems,
                    peak_cuda_allocated_bytes=(
                        torch.cuda.max_memory_allocated() if effective_device == "cuda" else None
                    ),
                    peak_cuda_reserved_bytes=(
                        torch.cuda.max_memory_reserved() if effective_device == "cuda" else None
                    ),
                    warnings=warnings,
                )
        except (DeviceUnavailableError, BackendSeparationError):
            raise
        except torch.cuda.OutOfMemoryError as exc:
            raise BackendSeparationError(
                "CUDA ran out of memory during separation.",
                details={"exception_type": type(exc).__name__},
            ) from exc
        except Exception as exc:
            raise BackendSeparationError(
                "audio-separator failed.",
                details={"exception_type": type(exc).__name__, "reason": str(exc)},
            ) from exc

    @staticmethod
    def _synchronize(device: str) -> None:
        if device == "cuda":
            torch.cuda.synchronize()

    @staticmethod
    def _resolve_outputs(output_dir: Path, returned: list[str]) -> tuple[Path, ...]:
        paths: list[Path] = []
        for item in returned:
            path = Path(item)
            if not path.is_absolute():
                path = output_dir / path
            paths.append(path.resolve())
        return tuple(paths)

    @staticmethod
    def _role_for(path: Path) -> str:
        match = _ROLE_RE.search(path.stem)
        return match.group(1).strip().lower() if match else path.stem

    @contextmanager
    def _project_environment(self) -> Iterator[None]:
        previous_model_dir = os.environ.get("AUDIO_SEPARATOR_MODEL_DIR")
        previous_path = os.environ.get("PATH", "")
        os.environ["AUDIO_SEPARATOR_MODEL_DIR"] = str(self.models_dir)
        if self.ffmpeg_bin is not None:
            os.environ["PATH"] = str(self.ffmpeg_bin) + os.pathsep + previous_path
        try:
            yield
        finally:
            if previous_model_dir is None:
                os.environ.pop("AUDIO_SEPARATOR_MODEL_DIR", None)
            else:
                os.environ["AUDIO_SEPARATOR_MODEL_DIR"] = previous_model_dir
            os.environ["PATH"] = previous_path
