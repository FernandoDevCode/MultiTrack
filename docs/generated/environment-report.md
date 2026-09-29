# StemLab environment report — Phase 0

Generated on 2026-09-29 in `C:\Users\User\Downloads\multiTrack`.

## Result: PASS

Phase 0 passes both required gates:

1. `audio-separator --env_info` completes in the project environment and
   detects the local FFmpeg, PyTorch CUDA, and ONNX CUDA provider.
2. BS-RoFormer completed a real separation on the RTX 5060 using CUDA and
   produced two valid, non-silent, duration-matched WAV stems.

No Phase 1 implementation was started. The selected checkpoint is approved
only as an **experimental technical smoke artifact**; this run makes no claim
about subjective separation quality or production-default suitability.

## Host and contained runtime

| Item | Verified value |
|---|---|
| OS | Windows 11 kernel `10.0.26200`, AMD64 |
| PowerShell | 7.6.5 |
| GPU | NVIDIA GeForce RTX 5060, 8151 MiB |
| Driver / driver CUDA UMD | 610.88 / 13.3 |
| Compute capability | 12.0 |
| Project Python | 3.12.10 in `.venv/` |
| Global Python state | Unchanged: 3.14 default and 3.11 registered; no registered 3.12 |
| PyTorch | 2.8.0+cu128 |
| PyTorch CUDA runtime | 12.8 |
| ONNX Runtime GPU | 1.26.0, CUDA provider available |
| audio-separator | 0.47.0 |

`scripts/dev-env.ps1` maps temp, pip/Torch/Hugging Face/Matplotlib caches and
the model directory into the repository. It activates `.venv` and prepends
`tools/ffmpeg/bin` only to the current process. Dot-sourcing it twice leaves
exactly one local FFmpeg PATH entry.

## FFmpeg local

- Distribution: Gyan.dev FFmpeg release Essentials 9.0.2, Windows x64
- Source URL: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`
- Upstream checksum URL:
  `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256`
- Archive size: 114,768,076 bytes
- Archive SHA-256:
  `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`
- Local distribution: `tools/ffmpeg/`

Extracted binaries:

| Binary | Bytes | SHA-256 |
|---|---:|---|
| `tools/ffmpeg/bin/ffmpeg.exe` | 105,423,872 | `3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec` |
| `tools/ffmpeg/bin/ffprobe.exe` | 105,221,120 | `f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52` |
| `tools/ffmpeg/bin/ffplay.exe` | 106,903,552 | `befbbd00a25965365f7fb3eed6ad5aa5f805eb70fabc567883a006de3b26c06f` |

Both `ffmpeg -version` and `ffprobe -version` report
`9.0.2-essentials_build-www.gyan.dev` from the paths above.

Command used for the environment gate:

```powershell
. .\scripts\dev-env.ps1
audio-separator --env_info
```

Result: exit code 0. The log reports the local FFmpeg 9.0.2, PyTorch
2.8.0+cu128, `CUDA is available in Torch`, ONNX Runtime GPU 1.26.0, and
`CUDAExecutionProvider available`.

## Model smoke artifact

- Friendly name: BS-RoFormer-Viperx-1297
- Architecture/backend: BS-RoFormer through audio-separator MDXC
- Task/stems: vocals and instrumental
- Checkpoint: `model_bs_roformer_ep_317_sdr_12.9755.ckpt`
- Origin page:
  `https://github.com/TRvlvr/model_repo/releases/tag/all_public_uvr_models`
- Checkpoint URL:
  `https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/model_bs_roformer_ep_317_sdr_12.9755.ckpt`
- Local path: `models/model_bs_roformer_ep_317_sdr_12.9755.ckpt`
- Size: 639,331,213 bytes
- SHA-256:
  `5b84f37e8d444c8cb30c79d77f613a41c05868ff9c9ac6c7049c00aefae115aa`
- Config URL:
  `https://github.com/nomadkaraoke/python-audio-separator/releases/download/model-configs/model_bs_roformer_ep_317_sdr_12.9755.yaml`
- Config local path: `models/model_bs_roformer_ep_317_sdr_12.9755.yaml`
- Config size / SHA-256: 2,273 bytes /
  `2bfdd16c656bd9519aba757cc4f8834b7ede675eb1e00ec4772d74ae1c41af7f`
- Weight license: unknown/not declared by the model repository
- Status: `experimental-smoke-only`; redistribution/default promotion is not
  authorized by this result

The model was selected from the catalog already supported by
`audio-separator`, downloaded with `--download_model_only` into a staging
directory under `models/`, hashed, size-checked, and only then promoted to the
final paths. Only this checkpoint and its YAML were downloaded.

## Real CUDA separation

The 10-second input is an original local fixture: Windows SAPI generated an
8.8946-second spoken phrase, which the smoke script resampled and mixed with
deterministic synthesized harmonics, chords, and percussion. It contains no
personal recording or external copyrighted music.

Exact separation command:

```powershell
. .\scripts\dev-env.ps1
python .\scripts\phase0-model-smoke.py --speech-wav .\.tmp\sapi-smoke-test.wav
```

Final evidence is saved at `.tmp/phase0-smoke/latest-result.json`; the complete
run is `.tmp/phase0-smoke/20260929-150610/`.

### Input

- File: `phase0-synthetic-mix.wav`
- Duration / format: 10.0 s, 44,100 Hz, stereo, PCM 16-bit WAV
- Size: 1,764,044 bytes
- SHA-256:
  `8e7c53fe531f2a105a5c734389736f7183940a5647a05b24509ca78b0ee54fa0`
- Input hash before and after separation: identical

### Runtime and CUDA evidence

| Measurement | Result |
|---|---:|
| Separator device | `cuda` |
| Model instance device | `cuda` |
| Effective precision | `autocast` |
| Model load | 2.646 s |
| Inference/export | 2.882 s |
| Total load + inference | 5.528 s |
| Peak CUDA allocated | 1,664,316,928 bytes (1.55 GiB) |
| Peak CUDA reserved | 2,462,056,448 bytes (2.29 GiB) |
| GPU total visible to Torch | 8,546,484,224 bytes (7.96 GiB) |

The backend reported `new_implementation_success: 1`, `total_failures: 0`,
selected CUDA before model load, and completed without OOM or CPU fallback.
The smoke was rerun from the cached model with no network access.

### Outputs

| Stem | Bytes | Duration | Sample rate/channels | RMS | Peak |
|---|---:|---:|---|---:|---:|
| Instrumental | 1,764,044 | 10.0 s | 44,100 Hz / stereo | 0.078112 | 0.366394 |
| Vocals | 1,764,044 | 10.0 s | 44,100 Hz / stereo | 0.074795 | 0.747498 |

Both outputs reopen through `soundfile`, contain only finite samples, are
non-empty/non-silent, and match input duration within the 0.1-second limit.
The only warning was the expected `Using soundfile for writing`; no device,
precision, OOM, loader, or fallback warning occurred.

## Diagnostics and tests

`scripts/doctor.py` now requires and verifies without running inference:

- Python 3.12.10 from the local `.venv`;
- Torch 2.8.0+cu128 and CUDA tensor execution;
- exact RTX 5060 identity and capability;
- local FFmpeg and ffprobe 9.0.2 by absolute workspace paths;
- audio-separator 0.47.0;
- all mutable directories contained by the repository;
- checkpoint/config existence, size, and SHA-256.

Validation commands:

```powershell
. .\scripts\dev-env.ps1
python .\scripts\doctor.py
python -m pip check
python -m pytest
```

Results: doctor PASS, no broken Python requirements, and pytest PASS. The test
suite validates the persisted smoke evidence without rerunning the model.

## Reproducibility and Git hygiene

- Exact Python environment is in `requirements-lock.txt`.
- `audioread==3.1.0` remains explicitly pinned for an undeclared import in
  audio-separator 0.47.0.
- `onnxruntime-gpu==1.26.0` remains pinned because 1.27+ PyPI defaults target
  CUDA 13, while the validated Torch runtime is CUDA 12.8.
- `.venv/`, `.cache/`, `.tmp/`, `tools/`, `models/`, outputs, and private
  benchmark content remain ignored by Git.
- No checkpoint, FFmpeg binary, cache, runtime, generated audio, or separated
  stem appears in `git status`.
- No driver, CUDA Toolkit, global package, PATH setting, remote, commit, tag,
  or release was created or changed.

Phase 0 is complete. Stop here; do not begin Phase 1 until separately requested.
