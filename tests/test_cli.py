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
    assert args.device == "auto"
    assert args.output_format == "wav"
    assert args.stem is None


def test_cli_accepts_forced_cpu_and_core_subset() -> None:
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
            "--device",
            "cpu",
            "--stem",
            "vocals",
            "--stem",
            "other",
        ]
    )
    assert args.device == "cpu"
    assert args.stem == ["vocals", "other"]


def test_cli_accepts_explicit_mp3_output() -> None:
    args = build_parser().parse_args(
        [
            "separate",
            "input.mp3",
            "--model",
            "models/model.ckpt",
            "--model-id",
            "model",
            "--model-sha256",
            "a" * 64,
            "--output",
            "outputs/run",
            "--format",
            "mp3",
        ]
    )
    assert args.input.name == "input.mp3"
    assert args.output_format == "mp3"
