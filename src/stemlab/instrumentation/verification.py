from __future__ import annotations

import json
from pathlib import Path

from stemlab.audio import sha256_file


EXPECTED_REPOSITORY = "laion/larger_clap_music"
EXPECTED_REVISION = "a0b4534a14f58e20944452dff00a22a06ce629d1"
EXPECTED_WEIGHT_SHA256 = "5c289311f4a030d768af7ffbfdecd01b008aa64824211899a4e59f4f9d154fd1"
REQUIRED_FILES = (
    "config.json",
    "merges.txt",
    "preprocessor_config.json",
    "pytorch_model.bin",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
)


def verify_detector_artifacts(model_dir: Path, receipt_path: Path) -> dict:
    model_dir = model_dir.resolve()
    receipt_path = receipt_path.resolve()
    if not receipt_path.is_file():
        raise RuntimeError(f"Instrument detector receipt is missing: {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("source_repository") != EXPECTED_REPOSITORY:
        raise RuntimeError("Instrument detector receipt repository mismatch.")
    if receipt.get("source_revision") != EXPECTED_REVISION:
        raise RuntimeError("Instrument detector receipt revision mismatch.")
    if receipt.get("weight_expected_sha256") != EXPECTED_WEIGHT_SHA256:
        raise RuntimeError("Instrument detector expected weight hash mismatch.")
    files = receipt.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("Instrument detector receipt is malformed.")
    for name in REQUIRED_FILES:
        expected = files.get(name)
        path = model_dir / name
        if not isinstance(expected, dict) or not path.is_file():
            raise RuntimeError(f"Instrument detector artifact is missing: {name}")
        if path.stat().st_size != int(expected.get("bytes", -1)):
            raise RuntimeError(f"Instrument detector artifact size mismatch: {name}")
        if sha256_file(path) != str(expected.get("sha256", "")):
            raise RuntimeError(f"Instrument detector artifact SHA-256 mismatch: {name}")
    weight = files["pytorch_model.bin"]
    if weight["sha256"] != EXPECTED_WEIGHT_SHA256:
        raise RuntimeError("Instrument detector weight SHA-256 is not approved.")
    if tuple(model_dir.glob("*.py")):
        raise RuntimeError("Remote Python code is not allowed in the detector directory.")
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    if config.get("model_type") != "clap" or "ClapModel" not in config.get("architectures", []):
        raise RuntimeError("Instrument detector config identity mismatch.")
    return receipt
