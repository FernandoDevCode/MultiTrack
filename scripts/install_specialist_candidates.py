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
MODEL_ROOT = REPO_ROOT / "models" / "experimental"
TMP_ROOT = REPO_ROOT / ".tmp" / "model-candidates" / "specialists"
RECEIPT_PATH = REPO_ROOT / ".tmp" / "specialist-candidates-install.json"


CANDIDATES = {
    "lead_rhythm_listra92": {
        "display_name": "Mel-Band Roformer Lead/Rhythm Guitar by listra92",
        "task": "lead_rhythm",
        "source_repo": "noblebarkrr/mvsepless_resources",
        "source_revision": "2749bf2dcd4d04f019c0581c49cb8891d77fddb4",
        "subdir": "mel_band_roformer",
        "checkpoint": "mbr_lead_rhythm_guitar_listra92.ckpt",
        "config": "mbr_lead_rhythm_guitar_listra92_config.yaml",
        "checkpoint_bytes": 337_073_664,
        "checkpoint_sha256": "b3c47bca33609ca1ba0bb2d2076410bfd1eb941b051b72afc1f3e24d12b17eef",
        "config_required_text": (
            "instruments:",
            "- Lead",
            "- Rhythm",
            "target_instrument: Lead",
            "sample_rate: 44100",
        ),
        "license": "unknown",
        "redistribution": "research-only",
    },
    "bass_xlancer": {
        "display_name": "BS Roformer Bass by Xlance",
        "task": "bass",
        "source_repo": "noblebarkrr/mvsepless_resources",
        "source_revision": "4e97e0fec0e787df4573cd8cb68a5a8d216dc120",
        "subdir": "bs_roformer",
        "checkpoint": "bs_bass_xlancer.ckpt",
        "config": "bs_bass_xlancer_config.yaml",
        "checkpoint_bytes": 204_411_168,
        "checkpoint_sha256": "c409465e3dccfd83fa34e6a807dbdae2f4f1db24f2f85a0fdc146b6fa828afff",
        "config_required_text": (
            "instruments:",
            "- bass",
            "- other",
            "target_instrument: bass",
            "sample_rate: 44100",
        ),
        "license": "unknown",
        "redistribution": "research-only",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_url(spec: dict, filename: str) -> str:
    return (
        f"https://huggingface.co/{spec['source_repo']}/resolve/"
        f"{spec['source_revision']}/{spec['subdir']}/{filename}"
    )


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
    headers = {"User-Agent": "StemLab-specialist-research/1.0"}
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
    header_size = response.headers.get("Content-Length")
    remaining = int(header_size) if header_size and header_size.isdigit() else None
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


def validate_candidate(candidate_id: str, directory: Path) -> dict:
    spec = CANDIDATES[candidate_id]
    checkpoint = directory / spec["checkpoint"]
    config = directory / spec["config"]

    if not checkpoint.is_file() or not config.is_file():
        raise RuntimeError(f"{candidate_id}: required artifact missing.")

    if checkpoint.stat().st_size != spec["checkpoint_bytes"]:
        raise RuntimeError(f"{candidate_id}: checkpoint size mismatch.")

    checkpoint_hash = sha256_file(checkpoint)
    if checkpoint_hash != spec["checkpoint_sha256"]:
        raise RuntimeError(
            f"{candidate_id}: checkpoint SHA-256 mismatch: {checkpoint_hash}"
        )

    config_text = config.read_text(encoding="utf-8")
    missing = [token for token in spec["config_required_text"] if token not in config_text]
    if missing:
        raise RuntimeError(
            f"{candidate_id}: config identity mismatch; missing {missing!r}"
        )

    return {
        "id": candidate_id,
        "display_name": spec["display_name"],
        "task": spec["task"],
        "source_repo": spec["source_repo"],
        "source_revision": spec["source_revision"],
        "license": spec["license"],
        "redistribution": spec["redistribution"],
        "checkpoint": {
            "path": str(checkpoint.resolve()),
            "bytes": checkpoint.stat().st_size,
            "sha256": checkpoint_hash,
        },
        "config": {
            "path": str(config.resolve()),
            "bytes": config.stat().st_size,
            "sha256": sha256_file(config),
        },
    }


def install_candidate(candidate_id: str) -> dict:
    spec = CANDIDATES[candidate_id]
    candidate_tmp = TMP_ROOT / candidate_id
    candidate_dir = MODEL_ROOT / candidate_id
    candidate_tmp.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    for key in ("checkpoint", "config"):
        filename = spec[key]
        target = candidate_dir / filename
        if target.is_file():
            continue
        temp = candidate_tmp / filename
        download(
            source_url(spec, filename),
            temp,
            expected_size=spec["checkpoint_bytes"] if key == "checkpoint" else None,
        )
        temp.replace(target)

    return validate_candidate(candidate_id, candidate_dir)


def write_receipt(items: list[dict]) -> None:
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": 1,
        "purpose": "StemLab v0.2 Checkpoint 3 specialist research only",
        "candidates": items,
    }
    RECEIPT_PATH.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def verify_installed() -> list[dict]:
    if not RECEIPT_PATH.is_file():
        raise RuntimeError(
            f"Receipt missing: {RECEIPT_PATH}. Run installer first."
        )
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    by_id = {
        item["id"]: item
        for item in receipt.get("candidates", [])
        if isinstance(item, dict) and "id" in item
    }
    verified = []
    for candidate_id in CANDIDATES:
        current = validate_candidate(candidate_id, MODEL_ROOT / candidate_id)
        previous = by_id.get(candidate_id)
        if previous is None:
            raise RuntimeError(f"Receipt entry missing: {candidate_id}")
        for artifact in ("checkpoint", "config"):
            if previous[artifact]["sha256"] != current[artifact]["sha256"]:
                raise RuntimeError(
                    f"{candidate_id}: {artifact} SHA-256 differs from receipt."
                )
        if previous["source_revision"] != current["source_revision"]:
            raise RuntimeError(f"{candidate_id}: source revision differs from receipt.")
        verified.append(current)
    return verified


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install/verify pinned StemLab specialist research candidates."
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    try:
        if args.verify_only:
            items = verify_installed()
        else:
            free = shutil.disk_usage(REPO_ROOT).free
            required = sum(spec["checkpoint_bytes"] for spec in CANDIDATES.values()) + 512 * 1024 * 1024
            if free < required:
                raise RuntimeError(
                    f"Not enough free space. Need about {required / (1024**3):.2f} GiB free."
                )
            items = [install_candidate(candidate_id) for candidate_id in CANDIDATES]
            write_receipt(items)
            items = verify_installed()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("\nPASS — specialist research candidates are verified.")
    print(f"Receipt: {RECEIPT_PATH}")
    for item in items:
        print(
            f"- {item['id']}: ckpt={item['checkpoint']['sha256']} "
            f"config={item['config']['sha256']}"
        )
    print("Research-only: no candidate has been promoted to a production/default model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
