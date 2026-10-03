from __future__ import annotations

import argparse
from pathlib import Path

from stemlab.app.specialist_benchmark import (
    run_internal_stage,
    run_specialist_benchmark,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the StemLab Checkpoint 3 specialist research gate."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--internal-stage",
        choices=("core", "g1", "g2", "b1"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--stage-output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--stage-result", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    if args.internal_stage:
        if args.stage_output is None or args.stage_result is None:
            raise SystemExit("internal stages require --stage-output and --stage-result")
        return run_internal_stage(
            repo_root=repo_root,
            stage=args.internal_stage,
            input_path=args.input,
            output_dir=args.stage_output,
            result_path=args.stage_result,
        )

    manifest_path, manifest = run_specialist_benchmark(
        repo_root=repo_root,
        input_path=args.input,
        run_id=args.run_id,
    )
    print(f"PASS - specialist benchmark completed: {manifest_path}")
    for stage in manifest["stages"]:
        timings = stage.get("timings") or {}
        device = stage.get("device") or {}
        print(
            f"- {stage['stage']}: total={timings.get('total_seconds')}s; "
            f"device={device.get('effective_device')}; "
            f"precision={device.get('effective_precision')}; "
            f"peak_allocated={device.get('peak_cuda_allocated_bytes')}; "
            f"peak_reserved={device.get('peak_cuda_reserved_bytes')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
