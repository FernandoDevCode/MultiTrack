# BS-RoFormer technical smoke — Phase 0

## Classification

- Task: vocals/instrumental two-stem separation
- Model: BS-RoFormer-Viperx-1297
- Backend: audio-separator 0.47.0, MDXC adapter
- Status: **experimental-smoke-only**
- Quality/default decision: not evaluated
- Weight license: unknown; do not redistribute or promote as a product default

## Artifact identity

- Checkpoint: `model_bs_roformer_ep_317_sdr_12.9755.ckpt`
- Source: `https://github.com/TRvlvr/model_repo/releases/tag/all_public_uvr_models`
- Bytes: 639,331,213
- SHA-256: `5b84f37e8d444c8cb30c79d77f613a41c05868ff9c9ac6c7049c00aefae115aa`
- Config SHA-256: `2bfdd16c656bd9519aba757cc4f8834b7ede675eb1e00ec4772d74ae1c41af7f`

## Reproduction

```powershell
. .\scripts\dev-env.ps1
python .\scripts\phase0-model-smoke.py --speech-wav .\.tmp\sapi-smoke-test.wav
```

Input: original 10-second, stereo, 44.1 kHz fixture combining local Windows
SAPI speech with deterministic synthesized accompaniment and percussion.

## Technical result

- Result: PASS
- Device: NVIDIA GeForce RTX 5060, CUDA, compute capability 12.0
- Torch: 2.8.0+cu128; effective precision: autocast
- Model load: 2.646 s
- Inference/export: 2.882 s
- Total: 5.528 s
- Peak CUDA allocated: 1.55 GiB
- Peak CUDA reserved: 2.29 GiB
- Loader stats: one new-implementation success, zero failures
- CPU fallback/OOM: none

Outputs:

| Stem | Duration | Channels | RMS | Peak |
|---|---:|---:|---:|---:|
| Instrumental | 10.0 s | 2 | 0.078112 | 0.366394 |
| Vocals | 10.0 s | 2 | 0.074795 | 0.747498 |

Both stems reopened successfully, contained finite samples, were non-silent,
and matched the input duration. The input remained byte-identical.

## Limitations

This fixture proves load, CUDA execution, memory fit, I/O, and basic output
invariants only. It has no ground truth and is not evidence of musical quality,
leakage performance, or suitability as a StemLab default. The checkpoint's
license remains unknown. Any promotion requires the later benchmark/registry
phase and a separate model-evaluation report.

