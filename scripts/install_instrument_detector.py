from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import urllib.error
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = REPO_ROOT / "models" / "instrument-detector" / "larger_clap_music"
TMP_DIR = REPO_ROOT / ".tmp" / "model-candidates" / "larger_clap_music"
RECEIPT_PATH = REPO_ROOT / ".tmp" / "larger-clap-music-install.json"

HF_REPO = "laion/larger_clap_music"
HF_REVISION = "a0b4534a14f58e20944452dff00a22a06ce629d1"
BASE_URL = f"https://huggingface.co/{HF_REPO}/resolve/{HF_REVISION}"

WEIGHT_NAME = "pytorch_model.bin"
WEIGHT_SIZE = 776_444_665
WEIGHT_SHA256 = "5c289311f4a030d768af7ffbfdecd01b008aa64824211899a4e59f4f9d154fd1"

REQUIRED_FILES = (
    "config.json",
    "merges.txt",
    "preprocessor_config.json",
    WEIGHT_NAME,
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def print_progress(name: str, downloaded: int, total: int | None, started: float) -> None:
    elapsed = max(time.monotonic() - started, 0.001)
    mib = downloaded / (1024 * 1024)
    speed = mib / elapsed
    if total:
        pct = downloaded * 100 / total
        total_mib = total / (1024 * 1024)
        print(
            f"\r{name}: {mib:,.1f}/{total_mib:,.1f} MiB "
            f"({pct:5.1f}%) @ {speed:,.1f} MiB/s",
            end="",
            flush=True,
        )
    else:
        print(f"\r{name}: {mib:,.1f} MiB @ {speed:,.1f} MiB/s", end="", flush=True)


def download(url: str, destination: Path, *, expected_size: int | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    existing = partial.stat().st_size if partial.exists() else 0

    headers = {"User-Agent": "StemLab-instrument-detector-bootstrap/1.0"}
    if existing:
        headers["Range"] = f"bytes={existing}-"

    request = urllib.request.Request(url, headers=headers)
    print(f"Downloading {destination.name}")
    if existing:
        print(f"Resuming from {existing / (1024 * 1024):,.1f} MiB")

    try:
        response = urllib.request.urlopen(request, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and expected_size and existing == expected_size:
            partial.replace(destination)
            return
        raise

    status = getattr(response, "status", 200)
    if existing and status != 206:
        existing = 0
        partial.unlink(missing_ok=True)

    mode = "ab" if existing and status == 206 else "wb"
    total_header = response.headers.get("Content-Length")
    remaining = int(total_header) if total_header and total_header.isdigit() else None
    total = existing + remaining if remaining is not None else expected_size

    started = time.monotonic()
    downloaded = existing
    with response, partial.open(mode) as stream:
        while True:
            chunk = response.read(4 * 1024 * 1024)
            if not chunk:
                break
            stream.write(chunk)
            downloaded += len(chunk)
            print_progress(destination.name, downloaded, total, started)
    print()

    if expected_size is not None and partial.stat().st_size != expected_size:
        raise RuntimeError(
            f"{destination.name}: size mismatch: {partial.stat().st_size} != {expected_size}"
        )
    partial.replace(destination)


def validate_metadata(directory: Path) -> None:
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    if config.get("model_type") != "clap" or "ClapModel" not in config.get("architectures", []):
        raise RuntimeError("Unexpected CLAP config.json identity.")

    preprocessor = json.loads(
        (directory / "preprocessor_config.json").read_text(encoding="utf-8")
    )
    if preprocessor.get("sampling_rate") != 48_000:
        raise RuntimeError("Unexpected CLAP sampling rate.")
    if preprocessor.get("max_length_s") != 10:
        raise RuntimeError("Unexpected CLAP max_length_s.")

    for name in REQUIRED_FILES:
        if not (directory / name).is_file():
            raise RuntimeError(f"Required detector artifact missing: {name}")

    unexpected_code = tuple(directory.glob("*.py"))
    if unexpected_code:
        raise RuntimeError(
            "Remote Python code is not allowed in the detector directory: "
            + ", ".join(path.name for path in unexpected_code)
        )


def validate_weight(directory: Path) -> None:
    weight = directory / WEIGHT_NAME
    if weight.stat().st_size != WEIGHT_SIZE:
        raise RuntimeError(
            f"Weight size mismatch: {weight.stat().st_size} != {WEIGHT_SIZE}"
        )
    actual = sha256_file(weight)
    if actual != WEIGHT_SHA256:
        raise RuntimeError(
            "Weight SHA-256 mismatch:\n"
            f"  expected: {WEIGHT_SHA256}\n"
            f"  actual:   {actual}"
        )


def build_receipt(directory: Path) -> dict[str, object]:
    validate_metadata(directory)
    validate_weight(directory)
    files = {}
    for name in REQUIRED_FILES:
        path = directory / name
        files[name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    return {
        "model": "LAION larger_clap_music",
        "task": "advisory zero-shot music instrumentation detection",
        "license": "apache-2.0",
        "source_repository": HF_REPO,
        "source_revision": HF_REVISION,
        "weight_expected_sha256": WEIGHT_SHA256,
        "files": files,
    }


def verify_receipt(receipt: dict[str, object], directory: Path) -> None:
    if receipt.get("source_repository") != HF_REPO:
        raise RuntimeError("Receipt repository mismatch.")
    if receipt.get("source_revision") != HF_REVISION:
        raise RuntimeError("Receipt revision mismatch.")

    files = receipt.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("Malformed detector receipt.")

    for name in REQUIRED_FILES:
        expected = files.get(name)
        if not isinstance(expected, dict):
            raise RuntimeError(f"Receipt entry missing for {name}.")
        path = directory / name
        if not path.is_file():
            raise RuntimeError(f"Installed detector artifact missing: {name}")
        if path.stat().st_size != int(expected["bytes"]):
            raise RuntimeError(f"Installed detector size mismatch: {name}")
        if sha256_file(path) != str(expected["sha256"]):
            raise RuntimeError(f"Installed detector SHA-256 mismatch: {name}")

    validate_metadata(directory)
    validate_weight(directory)


def install() -> dict[str, object]:
    free = shutil.disk_usage(REPO_ROOT).free
    required = WEIGHT_SIZE + 512 * 1024 * 1024
    if free < required:
        raise RuntimeError(
            f"Not enough free space. Need at least {required / (1024**3):.2f} GiB."
        )

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for name in REQUIRED_FILES:
        candidate = TMP_DIR / name
        if candidate.is_file():
            if name == WEIGHT_NAME:
                try:
                    if (
                        candidate.stat().st_size == WEIGHT_SIZE
                        and sha256_file(candidate) == WEIGHT_SHA256
                    ):
                        print(f"Reusing verified temporary {name}")
                        continue
                except OSError:
                    pass
            elif candidate.stat().st_size > 0:
                print(f"Reusing temporary {name}")
                continue
        download(
            f"{BASE_URL}/{name}",
            candidate,
            expected_size=WEIGHT_SIZE if name == WEIGHT_NAME else None,
        )

    validate_metadata(TMP_DIR)
    validate_weight(TMP_DIR)
    receipt = build_receipt(TMP_DIR)

    for name in REQUIRED_FILES:
        source = TMP_DIR / name
        destination = MODEL_DIR / name
        if destination.exists():
            expected = receipt["files"][name]
            if (
                destination.stat().st_size != int(expected["bytes"])
                or sha256_file(destination) != str(expected["sha256"])
            ):
                raise RuntimeError(
                    f"Refusing to replace different existing detector artifact: {destination}"
                )
            source.unlink(missing_ok=True)
        else:
            source.replace(destination)

    verify_receipt(receipt, MODEL_DIR)
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return receipt


def verify_installed() -> dict[str, object]:
    if not RECEIPT_PATH.is_file():
        raise RuntimeError(
            f"Receipt missing: {RECEIPT_PATH}. Run installer without --verify-only first."
        )
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    verify_receipt(receipt, MODEL_DIR)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and verify the pinned StemLab instrument detector."
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Do not use the network; verify installed files against the local receipt.",
    )
    args = parser.parse_args()

    try:
        receipt = verify_installed() if args.verify_only else install()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("\nPASS — instrument detector artifacts are verified.")
    print(f"Model dir: {MODEL_DIR}")
    print(f"Receipt: {RECEIPT_PATH}")
    print(f"Weight SHA-256: {receipt['files'][WEIGHT_NAME]['sha256']}")
    print("No separation models were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
