from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

from stemlab.audio import audio_signal_stats, probe_audio, sha256_file
from stemlab.domain import (
    DeviceInfo,
    FileArtifact,
    InputModifiedError,
    InputNotFoundError,
    InputValidationError,
    ModelArtifact,
    ModelIntegrityError,
    ModelMissingError,
    OutputPathError,
    OutputValidationError,
    SeparationErrorInfo,
    SeparationRequest,
    SeparationResult,
    StemArtifact,
    StemLabError,
    TimingInfo,
)
from stemlab.separation import SeparationBackend


class SeparationService:
    def __init__(self, backend: SeparationBackend, *, duration_tolerance_seconds: float = 0.1) -> None:
        self._backend = backend
        self._duration_tolerance_seconds = duration_tolerance_seconds

    def separate(self, request: SeparationRequest) -> SeparationResult:
        started_at = _utc_now()
        output_dir = request.output_dir.resolve()
        input_metadata = None
        model_artifact = None
        output_prepared = False
        try:
            input_path = request.input_path.resolve()
            self._validate_input(input_path)
            try:
                input_metadata = probe_audio(input_path, validate_finite=False)
            except OutputValidationError as exc:
                raise InputValidationError(
                    "Input audio is not readable.", details=exc.details
                ) from exc
            model_artifact = self._validate_model(request)
            self._prepare_output(output_dir, input_path)
            output_prepared = True

            backend_result = self._backend.separate(request, input_metadata)
            if sha256_file(input_path) != input_metadata.sha256:
                raise InputModifiedError(
                    "Input file changed during separation.",
                    details={"path": str(input_path)},
                )

            stems, validation_warnings = self._validate_stems(
                backend_result.stems, input_metadata, output_dir, input_path
            )
            warnings = tuple(backend_result.warnings) + validation_warnings
            result = SeparationResult(
                schema_version=1,
                success=True,
                started_at=started_at,
                completed_at=_utc_now(),
                input=input_metadata,
                model=model_artifact,
                backend=backend_result.backend_id,
                device=DeviceInfo(
                    requested_policy=request.device_policy,
                    effective_device=backend_result.effective_device,
                    effective_precision=backend_result.effective_precision,
                    peak_cuda_allocated_bytes=backend_result.peak_cuda_allocated_bytes,
                    peak_cuda_reserved_bytes=backend_result.peak_cuda_reserved_bytes,
                ),
                timings=TimingInfo(
                    model_load_seconds=backend_result.model_load_seconds,
                    inference_seconds=backend_result.inference_seconds,
                    total_seconds=backend_result.total_seconds,
                ),
                stems=stems,
                warnings=warnings,
                error=None,
                manifest_path=None,
            )
        except StemLabError as exc:
            result = self._failure_result(
                started_at, input_metadata, model_artifact, exc
            )
        except Exception as exc:  # Defensive boundary for CLI callers.
            result = self._failure_result(
                started_at,
                input_metadata,
                model_artifact,
                StemLabError(
                    "Unexpected separation engine failure.",
                    details={"exception_type": type(exc).__name__, "reason": str(exc)},
                ),
            )

        if output_prepared:
            result = self._write_manifest(output_dir, result)
        return result

    @staticmethod
    def _validate_input(path: Path) -> None:
        if not path.is_file():
            raise InputNotFoundError(
                f"Input audio does not exist: {path}", details={"path": str(path)}
            )

    @staticmethod
    def _validate_model(request: SeparationRequest) -> ModelArtifact:
        spec = request.model
        checkpoint = spec.checkpoint_path.resolve()
        if not checkpoint.is_file():
            raise ModelMissingError(
                f"Model checkpoint does not exist: {checkpoint}",
                details={"path": str(checkpoint)},
            )
        checkpoint_hash = sha256_file(checkpoint)
        if checkpoint_hash.lower() != spec.expected_sha256.lower():
            raise ModelIntegrityError(
                "Model checkpoint SHA-256 mismatch.",
                details={
                    "path": str(checkpoint),
                    "expected": spec.expected_sha256.lower(),
                    "actual": checkpoint_hash,
                },
            )

        configs: list[FileArtifact] = []
        for path, expected_hash in zip(
            spec.config_paths, spec.expected_config_sha256, strict=True
        ):
            resolved = path.resolve()
            if not resolved.is_file():
                raise ModelMissingError(
                    f"Model config does not exist: {resolved}",
                    details={"path": str(resolved)},
                )
            actual_hash = sha256_file(resolved)
            if actual_hash.lower() != expected_hash.lower():
                raise ModelIntegrityError(
                    "Model config SHA-256 mismatch.",
                    details={
                        "path": str(resolved),
                        "expected": expected_hash.lower(),
                        "actual": actual_hash,
                    },
                )
            configs.append(
                FileArtifact(
                    path=resolved, bytes=resolved.stat().st_size, sha256=actual_hash
                )
            )
        return ModelArtifact(
            model_id=spec.model_id,
            checkpoint=FileArtifact(
                path=checkpoint,
                bytes=checkpoint.stat().st_size,
                sha256=checkpoint_hash,
            ),
            configs=tuple(configs),
        )

    @staticmethod
    def _prepare_output(output_dir: Path, input_path: Path) -> None:
        if output_dir == input_path or output_dir in input_path.parents:
            raise OutputPathError(
                "Output directory cannot be the input file or contain it.",
                details={"output_dir": str(output_dir), "input": str(input_path)},
            )
        if output_dir.exists() and not output_dir.is_dir():
            raise OutputPathError(
                f"Output path is not a directory: {output_dir}",
                details={"path": str(output_dir)},
            )
        if output_dir.is_dir() and any(output_dir.iterdir()):
            raise OutputPathError(
                f"Output directory must be empty: {output_dir}",
                details={"path": str(output_dir)},
            )
        output_dir.mkdir(parents=True, exist_ok=True)

    def _validate_stems(
        self, backend_stems, input_metadata, output_dir: Path, input_path: Path
    ) -> tuple[tuple[StemArtifact, ...], tuple[str, ...]]:
        if not backend_stems:
            raise OutputValidationError("Backend returned no stems.")
        artifacts: list[StemArtifact] = []
        warnings: list[str] = []
        roles: set[str] = set()
        for stem in backend_stems:
            path = stem.path.resolve()
            if output_dir not in path.parents or path == input_path:
                raise OutputValidationError(
                    "Backend returned an output outside the requested directory.",
                    details={"path": str(path), "output_dir": str(output_dir)},
                )
            role = stem.role.strip().lower()
            if not role or role in roles:
                raise OutputValidationError(
                    "Stem roles must be non-empty and unique.", details={"role": role}
                )
            roles.add(role)
            metadata = probe_audio(path, validate_finite=True)
            rms, peak = audio_signal_stats(path)
            if rms <= 1e-10 or peak <= 1e-8:
                raise OutputValidationError(
                    "Stem is empty or silent.",
                    details={"path": str(path), "rms": rms, "peak": peak},
                )
            duration_error = abs(
                metadata.duration_seconds - input_metadata.duration_seconds
            )
            if duration_error > self._duration_tolerance_seconds:
                raise OutputValidationError(
                    "Stem duration does not match the input.",
                    details={
                        "path": str(path),
                        "input_seconds": input_metadata.duration_seconds,
                        "stem_seconds": metadata.duration_seconds,
                        "tolerance_seconds": self._duration_tolerance_seconds,
                    },
                )
            if metadata.sample_rate != input_metadata.sample_rate:
                warnings.append(
                    f"Stem {role!r} sample rate changed from "
                    f"{input_metadata.sample_rate} to {metadata.sample_rate}."
                )
            if metadata.channels != input_metadata.channels:
                warnings.append(
                    f"Stem {role!r} channel count changed from "
                    f"{input_metadata.channels} to {metadata.channels}."
                )
            artifacts.append(
                StemArtifact(
                    role=role,
                    path=metadata.path,
                    format=metadata.format,
                    duration_seconds=metadata.duration_seconds,
                    sample_rate=metadata.sample_rate,
                    channels=metadata.channels,
                    bytes=metadata.bytes,
                    sha256=metadata.sha256,
                    rms=rms,
                    peak=peak,
                )
            )
        return tuple(artifacts), tuple(warnings)

    @staticmethod
    def _failure_result(started_at, input_metadata, model_artifact, exc: StemLabError):
        return SeparationResult(
            schema_version=1,
            success=False,
            started_at=started_at,
            completed_at=_utc_now(),
            input=input_metadata,
            model=model_artifact,
            backend=None,
            device=None,
            timings=None,
            stems=(),
            warnings=(),
            error=SeparationErrorInfo(
                code=exc.code, message=exc.message, details=exc.details
            ),
            manifest_path=None,
        )

    @staticmethod
    def _write_manifest(output_dir: Path, result: SeparationResult) -> SeparationResult:
        manifest_path = output_dir / "manifest.json"
        finalized = replace(result, manifest_path=manifest_path)
        partial_path = output_dir / "manifest.json.partial"
        partial_path.write_text(
            json.dumps(finalized.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        partial_path.replace(manifest_path)
        return finalized


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
