from stemlab.cli import build_parser


def test_cli_exposes_one_headless_separate_command() -> None:
    args = build_parser().parse_args(
        [
            "separate",
            "input.wav",
            "--model",
            "models/model.ckpt",
            "--model-id",
            "model",
            "--model-sha256",
            "a" * 64,
            "--output",
            "outputs/run",
        ]
    )
    assert args.command == "separate"
    assert args.device == "cuda"
    assert args.output_format == "wav"
