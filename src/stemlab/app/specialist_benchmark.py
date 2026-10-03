from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable

from stemlab.app.modes import SIX_STEMS, build_request
from stemlab.app.separation_service import SeparationService
from stemlab.audio import audio_signal_stats, probe_audio, sha256_file
from stemlab.domain import DevicePolicy, OutputFormat, SeparationRequest
from stemlab.separation.specialist_candidates import (
    BASS_XLANCER,
    LEAD_RHYTHM_LISTRA92,
    SPECIALIST_CANDIDATES,
    build_specialist_model_spec,
    verify_all_specialist_candidates,
)


_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_PUBLIC_NAMES = {
    "G0": {"guitar": "guitar/G0_core_guitar.wav"},
    "G1": {
        "lead": "guitar/G1_direct_lead.wav",
        "rhythm": "guitar/G1_direct_rhythm.wav",
    },
    "G2": {
        "lead": "guitar/G2_twostage_lead.wav",
        "rhythm": "guitar/G2_twostage_rhythm.wav",
    },
    "B0": {"bass": "bass/B0_core_bass.wav"},
    "B1": {"bass": "bass/B1_specialist_bass.wav"},
}


class BenchmarkStageError(RuntimeError):
    def __init__(self, stage: str, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.stage = stage
        self.details = details or {}


StageRunner = Callable[..., dict]


def run_specialist_benchmark(
    *,
    repo_root: Path,
    input_path: Path,
    run_id: str | None = None,
    stage_runner: StageRunner | None = None,
) -> tuple[Path, dict]:
    """Run Core/G1/G2/B1 in isolated stages and publish the research manifest."""
    root = repo_root.resolve()
    source = input_path.resolve()
    source_metadata = probe_audio(source, validate_finite=True)
    input_hash_before = source_metadata.sha256
    verify_all_specialist_candidates(root / "models")

    selected_run_id = run_id or datetime.now(timezone.utc).strftime(
        "%Y%m%d-%H%M%S-%f"
    )
    if not _RUN_ID_RE.fullmatch(selected_run_id):
        raise ValueError("run_id must be 1-80 filename-safe characters")
    run_dir = (
        root / "bench" / "private" / _track_slug(source.stem) / selected_run_id
    ).resolve()
    private_root = (root / "bench" / "private").resolve()
    if private_root not in run_dir.parents:
        raise ValueError("benchmark output escaped bench/private")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"benchmark run directory is not empty: {run_dir}")
    (run_dir / "guitar").mkdir(parents=True, exist_ok=True)
    (run_dir / "bass").mkdir(parents=True, exist_ok=True)
    stages_root = run_dir / ".stages"
    stages_root.mkdir()

    runner = stage_runner or run_stage_subprocess
    manifest = _base_manifest(root, source_metadata, selected_run_id)
    manifest_path = run_dir / "manifest.json"

    try:
        core = _run_stage(
            runner,
            repo_root=root,
            stage="core",
            input_path=source,
            output_dir=stages_root / "core",
        )
        core_published = {}
        core_published.update(_publish_roles(core, _PUBLIC_NAMES["G0"], run_dir))
        core_published.update(_publish_roles(core, _PUBLIC_NAMES["B0"], run_dir))
        manifest["stages"].append(
            _stage_summary("core", ("G0", "B0"), core, core_published)
        )

        g1 = _run_stage(
            runner,
            repo_root=root,
            stage="g1",
            input_path=source,
            output_dir=stages_root / "g1",
        )
        g1_published = _publish_roles(g1, _PUBLIC_NAMES["G1"], run_dir)
        manifest["stages"].append(_stage_summary("g1", ("G1",), g1, g1_published))

        g0_path = run_dir / _PUBLIC_NAMES["G0"]["guitar"]
        g2 = _run_stage(
            runner,
            repo_root=root,
            stage="g2",
            input_path=g0_path,
            output_dir=stages_root / "g2",
        )
        g2_published = _publish_roles(g2, _PUBLIC_NAMES["G2"], run_dir)
        manifest["stages"].append(_stage_summary("g2", ("G2",), g2, g2_published))

        b1 = _run_stage(
            runner,
            repo_root=root,
            stage="b1",
            input_path=source,
            output_dir=stages_root / "b1",
        )
        b1_published = _publish_roles(b1, _PUBLIC_NAMES["B1"], run_dir)
        manifest["stages"].append(_stage_summary("b1", ("B1",), b1, b1_published))

        shutil.rmtree(stages_root)
        manifest["outputs"] = _validate_public_outputs(run_dir, source_metadata)
        input_hash_after = sha256_file(source)
        manifest["input"]["sha256_after"] = input_hash_after
        if input_hash_after != input_hash_before:
            raise RuntimeError("input SHA-256 changed during the specialist benchmark")
        manifest["status"] = "PASS"
    except Exception as exc:
        manifest["status"] = "FAILED"
        manifest["input"]["sha256_after"] = sha256_file(source)
        manifest["errors"].append(
            {
                "type": type(exc).__name__,
                "stage": getattr(exc, "stage", None),
                "message": str(exc),
                "details": getattr(exc, "details", {}),
            }
        )
        _write_json_atomic(manifest_path, manifest)
        raise

    _write_json_atomic(manifest_path, manifest)
    return manifest_path, manifest


def run_stage_subprocess(
    *, repo_root: Path, stage: str, input_path: Path, output_dir: Path
) -> dict:
    result_path = output_dir.parent / f"{stage}-result.json"
    env = _offline_project_environment(repo_root)
    command = [
        sys.executable,
        str(repo_root / "scripts" / "benchmark_specialists.py"),
        "--input",
        str(input_path),
        "--internal-stage",
        stage,
        "--stage-output",
        str(output_dir),
        "--stage-result",
        str(result_path),
    ]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    result = None
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
    if completed.returncode != 0 or not result or not result.get("success"):
        raise BenchmarkStageError(
            stage,
            f"benchmark stage {stage!r} failed; no fallback was attempted",
            details={
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
                "result": result,
            },
        )
    return result


def run_internal_stage(
    *,
    repo_root: Path,
    stage: str,
    input_path: Path,
    output_dir: Path,
    result_path: Path,
) -> int:
    if stage not in {"core", "g1", "g2", "b1"}:
        raise ValueError(f"unknown benchmark stage: {stage}")
    if stage == "core":
        request = build_request(
            repo_root=repo_root,
            input_path=input_path,
            mode_id=SIX_STEMS.mode_id,
            output_dir=output_dir,
            output_format=OutputFormat.WAV,
        )
    else:
        candidate = (
            LEAD_RHYTHM_LISTRA92 if stage in {"g1", "g2"} else BASS_XLANCER
        )
        request = SeparationRequest(
            input_path=input_path,
            model=build_specialist_model_spec(
                candidate.candidate_id, repo_root / "models"
            ),
            output_dir=output_dir,
            output_format=OutputFormat.WAV,
            device_policy=DevicePolicy.CUDA_REQUIRED,
            use_autocast=True,
            expected_roles=candidate.expected_roles,
        )

    # Importing the Torch-coupled adapter here keeps the orchestrator process light.
    from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend

    backend = AudioSeparatorBackend(
        models_dir=repo_root / "models",
        ffmpeg_bin=repo_root / "tools" / "ffmpeg" / "bin",
    )
    try:
        result = SeparationService(backend).separate(request)
        payload = result.to_dict()
        payload["runtime"] = _stage_runtime_versions()
        exit_code = 0 if result.success else 1
    except (Exception, SystemExit) as exc:
        payload = {
            "schema_version": 1,
            "success": False,
            "error": {
                "code": "stage_process_failure",
                "message": str(exc),
                "details": {"exception_type": type(exc).__name__},
            },
            "stems": [],
            "warnings": [],
            "runtime": _stage_runtime_versions(),
        }
        exit_code = 1
    _write_json_atomic(result_path, payload)
    return exit_code


def _run_stage(runner: StageRunner, **kwargs) -> dict:
    result = runner(**kwargs)
    if not result.get("success"):
        raise BenchmarkStageError(
            kwargs["stage"],
            f"benchmark stage {kwargs['stage']!r} failed; no fallback was attempted",
            details={"result": result},
        )
    return result


def _publish_roles(result: dict, role_names: dict[str, str], run_dir: Path) -> dict:
    by_role = {item["role"].strip().lower(): item for item in result.get("stems", [])}
    published: dict[str, str] = {}
    for role, relative_name in role_names.items():
        if role not in by_role:
            raise BenchmarkStageError(
                "publish",
                f"stage result is missing expected role {role!r}",
                details={"actual_roles": sorted(by_role)},
            )
        source = Path(by_role[role]["path"]).resolve()
        destination = (run_dir / relative_name).resolve()
        if run_dir not in destination.parents:
            raise RuntimeError("published output escaped benchmark run directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)
        published[role] = str(destination)
    return published


def _validate_public_outputs(run_dir: Path, input_metadata) -> list[dict]:
    expected = [
        relative
        for role_map in _PUBLIC_NAMES.values()
        for relative in role_map.values()
    ]
    outputs = []
    for relative in expected:
        path = run_dir / relative
        metadata = probe_audio(path, validate_finite=True)
        rms, peak = audio_signal_stats(path)
        if abs(metadata.duration_seconds - input_metadata.duration_seconds) > 0.1:
            raise RuntimeError(f"published output duration mismatch: {path}")
        if metadata.sample_rate != input_metadata.sample_rate:
            raise RuntimeError(f"published output sample-rate mismatch: {path}")
        if metadata.channels != input_metadata.channels:
            raise RuntimeError(f"published output channel-count mismatch: {path}")
        if rms <= 1e-10 or peak <= 1e-8:
            raise RuntimeError(f"published output is silent: {path}")
        outputs.append(
            {
                "name": path.stem,
                "path": str(path.resolve()),
                "format": metadata.format,
                "duration_seconds": metadata.duration_seconds,
                "sample_rate": metadata.sample_rate,
                "channels": metadata.channels,
                "bytes": metadata.bytes,
                "sha256": metadata.sha256,
                "rms": rms,
                "peak": peak,
            }
        )
    return outputs


def _stage_summary(
    stage: str, variants: tuple[str, ...], result: dict, published: dict[str, str]
) -> dict:
    return {
        "stage": stage,
        "pipeline_variants": list(variants),
        "model": result.get("model"),
        "backend": result.get("backend"),
        "device": result.get("device"),
        "timings": result.get("timings"),
        "runtime": result.get("runtime"),
        "published_roles": published,
        "warnings": result.get("warnings", []),
    }


def _base_manifest(repo_root: Path, input_metadata, run_id: str) -> dict:
    return {
        "schema_version": 1,
        "checkpoint": "StemLab v0.2 Checkpoint 3",
        "status": "RUNNING",
        "run_id": run_id,
        "input": {
            "path": str(input_metadata.path),
            "sha256_before": input_metadata.sha256,
            "sha256_after": None,
            "bytes": input_metadata.bytes,
            "duration_seconds": input_metadata.duration_seconds,
            "sample_rate": input_metadata.sample_rate,
            "channels": input_metadata.channels,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "audio_separator": importlib.metadata.version("audio-separator"),
            "isolation": "one subprocess per heavy stage",
            "network": "offline environment; local verified artifacts only",
            "precision_requested": "autocast",
        },
        "models": {
            "core": {
                "model_id": SIX_STEMS.model_id,
                "checkpoint_sha256": SIX_STEMS.checkpoint_sha256,
                "config_sha256": [value for _, value in SIX_STEMS.config_files],
            },
            "specialists": [
                {
                    "candidate_id": item.candidate_id,
                    "task": item.task,
                    "checkpoint_sha256": item.checkpoint_sha256,
                    "config_sha256": item.config_sha256,
                    "source_repo": item.source_repo,
                    "source_revision": item.source_revision,
                    "license": item.license,
                    "redistribution": item.redistribution,
                }
                for item in SPECIALIST_CANDIDATES
            ],
        },
        "core_reuse": {
            "core_runs": 1,
            "G0_and_B0_from_same_run": True,
            "G2_input": "G0_core_guitar",
        },
        "stages": [],
        "outputs": [],
        "warnings": [],
        "errors": [],
    }


def _offline_project_environment(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    cache = repo_root / ".cache"
    temporary = repo_root / ".tmp"
    values = {
        "PIP_CACHE_DIR": cache / "pip",
        "TORCH_HOME": cache / "torch",
        "HF_HOME": cache / "huggingface",
        "XDG_CACHE_HOME": cache,
        "MPLCONFIGDIR": cache / "matplotlib",
        "TEMP": temporary,
        "TMP": temporary,
        "AUDIO_SEPARATOR_MODEL_DIR": repo_root / "models",
    }
    for name, value in values.items():
        value.mkdir(parents=True, exist_ok=True)
        env[name] = str(value)
    env.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "ALL_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "127.0.0.1,localhost",
        }
    )
    ffmpeg_bin = str(repo_root / "tools" / "ffmpeg" / "bin")
    env["PATH"] = ffmpeg_bin + os.pathsep + env.get("PATH", "")
    return env


def _stage_runtime_versions() -> dict[str, str | None]:
    import torch

    return {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "audio_separator": importlib.metadata.version("audio-separator"),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    partial.replace(path)


def _track_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or "track"
