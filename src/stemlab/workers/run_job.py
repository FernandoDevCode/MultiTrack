from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from stemlab.workers.protocol import encode_event


def configure_worker_stdout() -> None:
    """Keep the line-delimited worker protocol UTF-8 on Windows as well."""
    sys.stdout.reconfigure(encoding="utf-8", errors="strict", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stemlab-worker")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("wav", "flac", "mp3"), required=True)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--stem", action="append", default=None)
    return parser


def _emit(event_type: str, message: str, payload=None) -> None:
    print(encode_event(event_type, message=message, payload=payload), flush=True)


def main(argv: list[str] | None = None) -> int:
    configure_worker_stdout()
    args = build_parser().parse_args(argv)
    if args.device == "cpu":
        # audio-separator 0.47.0 selects CUDA during construction whenever Torch
        # can see it. This must happen before importing the adapter (and Torch).
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    from stemlab.app import SeparationService, build_request
    from stemlab.domain import DevicePolicy, OutputFormat
    from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend

    repo_root = Path(__file__).resolve().parents[3]
    _emit("started", "Worker iniciado.", {"output_dir": str(args.output.resolve())})
    try:
        request = build_request(
            repo_root=repo_root,
            input_path=args.input,
            mode_id=args.mode,
            output_dir=args.output,
            output_format=OutputFormat(args.format.upper()),
            device_policy=DevicePolicy(args.device),
            requested_roles=None if args.stem is None else tuple(args.stem),
        )
        if args.device == "cpu":
            status = "CPU selecionada. A separação pode ser lenta; executando em FP32."
        elif args.device == "cuda":
            status = "Validando modelo e executando separação CUDA obrigatória."
        else:
            status = "Detectando CUDA no worker; sem GPU disponível, será usada CPU em FP32."
        _emit("status", status)
        backend = AudioSeparatorBackend(
            models_dir=repo_root / "models",
            ffmpeg_bin=repo_root / "tools" / "ffmpeg" / "bin",
            on_progress=lambda progress: _emit("progress", "", progress.to_dict()),
        )
        result = SeparationService(
            backend, on_progress=lambda progress: _emit("progress", "", progress.to_dict())
        ).separate(request)
        payload = {"result": result.to_dict(), "output_dir": str(args.output.resolve())}
        if not result.success:
            message = result.error.message if result.error else "Falha sem detalhe estruturado."
            _emit("failed", message, payload)
            return 1
        _emit("completed", "Separação concluída.", payload)
        return 0
    except Exception as exc:
        _emit(
            "failed",
            "Falha inesperada no worker.",
            {"error_type": type(exc).__name__, "reason": str(exc)},
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
