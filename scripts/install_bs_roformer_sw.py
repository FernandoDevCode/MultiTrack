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
MODELS_DIR = REPO_ROOT / "models"
TMP_DIR = REPO_ROOT / ".tmp" / "model-candidates" / "bs-roformer-sw"
RECEIPT_PATH = REPO_ROOT / ".tmp" / "bs-roformer-sw-install.json"

# Pin downloads to one immutable Hugging Face repository revision.
HF_REVISION = "3b39120409f3c2d50e9cc4c391f4169131e9d643"
BASE_URL = (
    "https://huggingface.co/lainlives/audio-separator-models/resolve/"
    + HF_REVISION
)

CHECKPOINT_NAME = "BS-Roformer-SW.ckpt"
CHECKPOINT_URL = f"{BASE_URL}/{CHECKPOINT_NAME}"
CHECKPOINT_SIZE = 699_412_152
CHECKPOINT_SHA256 = (
    "24e7d35ee9c64415673d3fd33e06a67cac2c103c5df6267ba1576459c775916e"
)

CONFIG_NAME = "BS-Roformer-SW.yaml"
CONFIG_URL = f"{BASE_URL}/{CONFIG_NAME}"
# Hugging Face serves this small file with this Git blob object id.
CONFIG_GIT_BLOB_SHA1 = "49760ce0b48d341ee70760803dd59f4cb0982728"

EXPECTED_STEMS_TEXT = (
    "instruments: ['bass', 'drums', 'other', 'vocals', 'guitar', 'piano']"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    digest = hashlib.sha1()
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
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
        print(
            f"\r{name}: {mib:,.1f} MiB @ {speed:,.1f} MiB/s",
            end="",
            flush=True,
        )


def download(url: str, destination: Path, *, expected_size: int | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    existing = partial.stat().st_size if partial.exists() else 0

    headers = {"User-Agent": "StemLab-model-bootstrap/1.0"}
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
            f"{destination.name}: size mismatch: "
            f"{partial.stat().st_size} != {expected_size}"
        )
    partial.replace(destination)


def verify_checkpoint(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"Checkpoint missing: {path}")
    size = path.stat().st_size
    if size != CHECKPOINT_SIZE:
        raise RuntimeError(
            f"Checkpoint size mismatch: {size} != {CHECKPOINT_SIZE}"
        )
    actual = sha256_file(path)
    if actual != CHECKPOINT_SHA256:
        raise RuntimeError(
            "Checkpoint SHA-256 mismatch:\n"
            f"  expected: {CHECKPOINT_SHA256}\n"
            f"  actual:   {actual}"
        )
    return {"bytes": size, "sha256": actual}


def verify_config(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"Config missing: {path}")

    blob_sha1 = git_blob_sha1(path)
    if blob_sha1 != CONFIG_GIT_BLOB_SHA1:
        raise RuntimeError(
            "Config Git blob SHA-1 mismatch:\n"
            f"  expected: {CONFIG_GIT_BLOB_SHA1}\n"
            f"  actual:   {blob_sha1}"
        )

    text = path.read_text(encoding="utf-8")
    if "num_stems: 6" not in text or EXPECTED_STEMS_TEXT not in text:
        raise RuntimeError("Config does not declare the expected six stems.")

    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "git_blob_sha1": blob_sha1,
    }


def install() -> dict[str, object]:
    free = shutil.disk_usage(REPO_ROOT).free
    required = CHECKPOINT_SIZE + 250 * 1024 * 1024
    if free < required:
        raise RuntimeError(
            f"Not enough free space. Need at least {required / (1024**3):.2f} GiB."
        )

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    candidate_config = TMP_DIR / CONFIG_NAME
    candidate_checkpoint = TMP_DIR / CHECKPOINT_NAME

    # Small config first.
    download(CONFIG_URL, candidate_config)
    config_info = verify_config(candidate_config)
    print(
        f"Config verified: git-blob-sha1={config_info['git_blob_sha1']} "
        f"sha256={config_info['sha256']}"
    )

    download(
        CHECKPOINT_URL,
        candidate_checkpoint,
        expected_size=CHECKPOINT_SIZE,
    )
    checkpoint_info = verify_checkpoint(candidate_checkpoint)
    print(f"Checkpoint verified: sha256={checkpoint_info['sha256']}")

    final_config = MODELS_DIR / CONFIG_NAME
    final_checkpoint = MODELS_DIR / CHECKPOINT_NAME

    if final_config.exists():
        verify_config(final_config)
        candidate_config.unlink(missing_ok=True)
    else:
        candidate_config.replace(final_config)

    if final_checkpoint.exists():
        verify_checkpoint(final_checkpoint)
        candidate_checkpoint.unlink(missing_ok=True)
    else:
        candidate_checkpoint.replace(final_checkpoint)

    return verify_installed()


def verify_installed() -> dict[str, object]:
    config_path = MODELS_DIR / CONFIG_NAME
    checkpoint_path = MODELS_DIR / CHECKPOINT_NAME

    config_info = verify_config(config_path)
    checkpoint_info = verify_checkpoint(checkpoint_path)

    receipt = {
        "model": "BS-RoFormer SW by jarredou",
        "source_repository": "lainlives/audio-separator-models",
        "source_revision": HF_REVISION,
        "checkpoint": {
            "path": str(checkpoint_path.relative_to(REPO_ROOT)),
            "url": CHECKPOINT_URL,
            **checkpoint_info,
        },
        "config": {
            "path": str(config_path.relative_to(REPO_ROOT)),
            "url": CONFIG_URL,
            **config_info,
        },
        "expected_stems": [
            "bass",
            "drums",
            "other",
            "vocals",
            "guitar",
            "piano",
        ],
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and verify the pinned BS-RoFormer SW artifacts."
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Do not use the network; verify the already-installed files.",
    )
    args = parser.parse_args()

    try:
        receipt = verify_installed() if args.verify_only else install()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("\nPASS — BS-RoFormer SW artifacts are verified.")
    print(f"Receipt: {RECEIPT_PATH}")
    print(
        "YAML SHA-256 to pin in StemLab: "
        + str(receipt["config"]["sha256"])
    )
    print("The old htdemucs_6s files were NOT removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
