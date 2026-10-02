from __future__ import annotations

import argparse
from pathlib import Path
import sys

from stemlab.app import InstrumentationAnalysisService
from stemlab.app.audio_windows import FfmpegWindowDecoder
from stemlab.instrumentation import ClapInstrumentDetector
from stemlab.workers.protocol import encode_event


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stemlab-instrument-analysis-worker")
    parser.add_argument("--input", type=Path, required=True)
    return parser


def _emit(event_type: str, message: str, payload=None) -> None:
    print(encode_event(event_type, message=message, payload=payload), flush=True)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="strict", newline="\n")
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[3]
    detector = ClapInstrumentDetector(
        model_dir=repo_root / "models" / "instrument-detector" / "larger_clap_music",
        receipt_path=repo_root / ".tmp" / "larger-clap-music-install.json",
    )
    _emit("started", "Worker de análise iniciado.")
    try:
        _emit("status", "Verificando detector CLAP local e analisando janelas em CUDA.")
        result = InstrumentationAnalysisService(
            detector,
            FfmpegWindowDecoder(repo_root / "tools" / "ffmpeg" / "bin"),
        ).analyze(args.input)
        _emit("completed", "Análise de instrumentos concluída.", {"result": result.to_dict()})
        return 0
    except Exception as exc:
        _emit(
            "failed",
            f"Falha na análise de instrumentos: {exc}",
            {"error_type": type(exc).__name__, "reason": str(exc)},
        )
        return 1
    finally:
        detector.close()


if __name__ == "__main__":
    raise SystemExit(main())
