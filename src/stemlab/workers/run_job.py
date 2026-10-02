from __future__ import annotations

import argparse
from pathlib import Path
import sys

from stemlab.app import SeparationService, build_request
from stemlab.domain import OutputFormat
from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend
from stemlab.workers.protocol import encode_event


def configure_worker_stdout() -> None:
    """Keep the line-delimited worker protocol UTF-8 on Windows as well."""
    sys.stdout.reconfigure(encoding="utf-8", errors="strict", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stemlab-worker")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("wav", "flac"), required=True)
    return parser


def _emit(event_type: str, message: str, payload=None) -> None:
    print(encode_event(event_type, message=message, payload=payload), flush=True)


def main(argv: list[str] | None = None) -> int:
    configure_worker_stdout()
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[3]
    _emit("started", "Worker iniciado.", {"output_dir": str(args.output.resolve())})
    try:
        request = build_request(
            repo_root=repo_root,
            input_path=args.input,
            mode_id=args.mode,
            output_dir=args.output,
            output_format=OutputFormat(args.format.upper()),
        )
        _emit("status", "Validando modelo e executando separação CUDA.")
        backend = AudioSeparatorBackend(
            models_dir=repo_root / "models",
            ffmpeg_bin=repo_root / "tools" / "ffmpeg" / "bin",
        )
        result = SeparationService(backend).separate(request)
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
