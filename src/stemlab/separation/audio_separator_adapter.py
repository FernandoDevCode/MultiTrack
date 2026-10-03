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
from audio_separator.separator.architectures.mdxc_separator import MDXCSeparator
from audio_separator.separator.roformer.roformer_loader import RoformerLoader
from audio_separator.separator.uvr_lib_v5.roformer.mel_band_roformer import (
    MaskEstimator,
)

from stemlab.domain import (
    AudioMetadata,
    BackendSeparationError,
    DevicePolicy,
    DeviceUnavailableError,
    SeparationRequest,
)
from stemlab.separation.backend import BackendResult, BackendStem
from stemlab.separation.specialist_candidates import (
    LEAD_RHYTHM_LISTRA92,
    SpecialistCandidate,
    resolve_verified_specialist,
)


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
            "demucs_params": {
                "segment_size": "Default",
                "shifts": 2,
                "overlap": 0.25,
                "segments_enabled": True,
            },
        }

        try:
            with self._project_environment():
                specialist = resolve_verified_specialist(request.model, self.models_dir)
                separator = self._separator_for(specialist, separator_kwargs)
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
                backend_filename = (
                    request.model.backend_filename or request.model.checkpoint_path.name
                )
                allowed_filenames = {
                    request.model.checkpoint_path.name,
                    *(path.name for path in request.model.config_paths),
                }
                if backend_filename not in allowed_filenames:
                    raise BackendSeparationError(
                        "Backend model identifier is not one of the verified artifacts.",
                        details={"backend_filename": backend_filename},
                    )
                separator.load_model(backend_filename)
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

    @staticmethod
    def _separator_for(
        specialist: SpecialistCandidate | None, separator_kwargs: dict
    ) -> Separator:
        if specialist is None:
            return Separator(**separator_kwargs)
        return _VerifiedLocalSpecialistSeparator(
            specialist=specialist,
            **separator_kwargs,
        )

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


class _VerifiedLocalSpecialistSeparator(Separator):
    """Resolve exactly one verified local specialist without registry/network access."""

    def __init__(self, *, specialist: SpecialistCandidate, **kwargs) -> None:
        self._stemlab_specialist = specialist
        super().__init__(**kwargs)

    def download_model_files(self, model_filename):
        candidate = self._stemlab_specialist
        if model_filename != candidate.checkpoint_relative_path.name:
            raise ValueError(
                f"Model file {model_filename!r} is not allowlisted for "
                f"{candidate.candidate_id!r}."
            )
        checkpoint = Path(self.model_file_dir) / candidate.checkpoint_relative_path
        config = Path(self.model_file_dir) / candidate.config_relative_path
        self.model_is_uvr_vip = False
        self.model_friendly_name = candidate.display_name
        return (
            model_filename,
            "MDXC",
            candidate.display_name,
            str(checkpoint.resolve()),
            str(config.resolve()),
        )

    def load_model(self, model_filename="", force_reload=False):
        candidate = self._stemlab_specialist
        if candidate.candidate_id != LEAD_RHYTHM_LISTRA92.candidate_id:
            return super().load_model(model_filename, force_reload=force_reload)
        if model_filename != candidate.checkpoint_relative_path.name:
            raise ValueError(
                f"Model file {model_filename!r} is not allowlisted for "
                f"{candidate.candidate_id!r}."
            )
        if (
            not force_reload
            and self.model_instance is not None
            and self._loaded_model_filename == model_filename
        ):
            return

        (
            resolved_filename,
            model_type,
            friendly_name,
            model_path,
            config_path,
        ) = self.download_model_files(model_filename)
        if model_type != "MDXC":
            raise ValueError(f"Unexpected specialist model type: {model_type}")
        model_data = self.load_model_data_from_yaml(config_path)
        common_params = {
            "logger": self.logger,
            "log_level": self.log_level,
            "torch_device": self.torch_device,
            "torch_device_cpu": self.torch_device_cpu,
            "torch_device_mps": self.torch_device_mps,
            "onnx_execution_provider": self.onnx_execution_provider,
            "model_name": resolved_filename.split(".")[0],
            "model_path": model_path,
            "model_data": model_data,
            "output_format": self.output_format,
            "output_bitrate": self.output_bitrate,
            "output_dir": self.output_dir,
            "normalization_threshold": self.normalization_threshold,
            "amplification_threshold": self.amplification_threshold,
            "output_single_stem": self.output_single_stem,
            "invert_using_spec": self.invert_using_spec,
            "sample_rate": self.sample_rate,
            "use_soundfile": self.use_soundfile,
            "use_autocast": self.use_autocast,
            "use_native_fp16": self.use_native_fp16,
            "use_torch_compile": self.use_torch_compile,
        }
        model_instance = _LeadRhythmMDXCSeparator(
            common_config=common_params,
            arch_config=self.arch_specific_params[model_type],
        )
        resolve_policy = getattr(model_instance, "resolve_execution_policy", None)
        if callable(resolve_policy) and not getattr(
            model_instance, "_execution_policy_resolved", False
        ):
            resolve_policy(model_type.lower())

        self.model_instance = model_instance
        self.model_filename = model_filename
        self.model_filenames = [model_filename]
        self._loaded_model_filename = resolved_filename
        self.model_friendly_name = friendly_name
        self.model_is_uvr_vip = False
        self._loaded_model_friendly_name = friendly_name
        self._loaded_model_is_uvr_vip = False


class _LeadRhythmMDXCSeparator(MDXCSeparator):
    def load_model(self):
        self.roformer_loader = _LeadRhythmRoformerLoader()
        return super().load_model()


class _LeadRhythmRoformerLoader(RoformerLoader):
    """Work around the pinned 0.47.0 mask-estimator factor propagation bug."""

    def _create_mel_band_roformer(self, config):
        model = super()._create_mel_band_roformer(config)
        expansion_factor = config.get("mlp_expansion_factor", 4)
        if expansion_factor == 4:
            return model

        if not model.mask_estimators:
            raise RuntimeError("MelBandRoformer created without mask estimators")
        dim_inputs = model.mask_estimators[0].dim_inputs
        model.mask_estimators = torch.nn.ModuleList(
            [
                MaskEstimator(
                    dim=config["dim"],
                    dim_inputs=dim_inputs,
                    depth=config.get("mask_estimator_depth", 1),
                    mlp_expansion_factor=expansion_factor,
                )
                for _ in range(config.get("num_stems", 1))
            ]
        )
        return model
