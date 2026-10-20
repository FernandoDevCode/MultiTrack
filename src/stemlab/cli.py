from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stemlab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    separate = subparsers.add_parser("separate", help="Run one headless separation")
    separate.add_argument("input", type=Path)
    separate.add_argument("--model", type=Path, required=True)
    separate.add_argument("--model-id", required=True)
    separate.add_argument("--model-sha256", required=True)
    separate.add_argument("--model-config", type=Path, action="append", default=[])
    separate.add_argument("--model-config-sha256", action="append", default=[])
    separate.add_argument("--backend-filename")
    separate.add_argument("--expect-stem", action="append", default=[])
    separate.add_argument(
        "--stem",
        action="append",
        default=None,
        help="Core Stem to retain; repeat for multiple roles (default: all outputs)",
    )
    separate.add_argument("--output", type=Path, required=True)
    separate.add_argument(
        "--format",
        choices=("wav", "flac", "mp3"),
        default="wav",
        dest="output_format",
        help="Stem output format; MP3 is a lossy 320 kbps export.",
    )
    separate.add_argument("--device", choices=("cuda", "auto", "cpu"), default="auto")
    separate.add_argument("--no-autocast", action="store_true")
    separate.add_argument("--json", action="store_true", dest="print_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if len(args.model_config) != len(args.model_config_sha256):
        raise SystemExit(
            "Each --model-config requires one matching --model-config-sha256."
        )

    if args.device == "cpu":
        # Force CPU visibility before importing the adapter and therefore Torch.
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

    from stemlab.app import SeparationService
    from stemlab.domain import DevicePolicy, ModelSpec, OutputFormat, SeparationRequest
    from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend

    repo_root = Path(__file__).resolve().parents[2]
    request = SeparationRequest(
        input_path=args.input,
        model=ModelSpec(
            model_id=args.model_id,
            checkpoint_path=args.model,
            expected_sha256=args.model_sha256,
            config_paths=tuple(args.model_config),
            expected_config_sha256=tuple(args.model_config_sha256),
            backend_filename=args.backend_filename,
        ),
        output_dir=args.output,
        output_format=OutputFormat(args.output_format.upper()),
        device_policy=DevicePolicy(args.device),
        use_autocast=not args.no_autocast,
        expected_roles=tuple(args.expect_stem),
        requested_roles=None if args.stem is None else tuple(args.stem),
    )
    backend = AudioSeparatorBackend(
        models_dir=repo_root / "models",
        ffmpeg_bin=repo_root / "tools" / "ffmpeg" / "bin",
    )
    result = SeparationService(backend).separate(request)
    if args.print_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    elif result.manifest_path:
        print(result.manifest_path)
    elif result.error:
        print(f"{result.error.code}: {result.error.message}")
    return 0 if result.success else 1
