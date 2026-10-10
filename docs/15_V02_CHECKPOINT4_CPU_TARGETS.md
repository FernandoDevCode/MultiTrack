# StemLab v0.2 — Checkpoint 4: CPU + Selection of Desired Stems

**Status:** approved implementation spec; NOT YET IMPLEMENTED.  
**Base:** `main` after Checkpoint 3 technical PASS. Checkpoint 3 specialists remain research-only until human listening gate.

## Purpose

The user must be able to:
1. separate music on a Windows PC without a NVIDIA GPU, using CPU intentionally;
2. choose exactly which **currently producible** musical stems will be delivered into the player/output directory/export;
3. understand honestly whether the selection saves inference time.

This checkpoint does not improve source-separation quality or introduce specialist production routing.

## Reality of computation savings

The current model `BS-RoFormer SW` is a **six-output** model (vocals, drums, bass, guitar, piano, other).

- Asking for only one/two of these targets does **not** normally reduce the model's six-source forward-pass cost.
- The library's `output_single_stem` option can suppress file writing for one target. That does **not** imply skipping six-source inference.
- Persisting fewer files **does** reduce final disk usage and perhaps writing/validation overhead. Do not promise a material speed-up without measurement.
- Substantial future speed savings come when specialist pipeline stages are skipped because they were not requested.
- Do not automatically route to unapproved Lead/Rhythm or Bass research candidates just because a target was selected.

## Supported capability in Checkpoint 4

```text
Source audio
    ↓
Device choice: Automatic / NVIDIA CUDA / CPU
    ↓
Select deliverable stems:
  [x] Vocals
  [x] Drums
  [x] Bass
  [x] Guitar
  [x] Piano
  [x] Other
    ↓
BS-RoFormer SW six-output inference (one pass)
    ↓
keep ONLY requested outputs
    ↓
player / export / manifest show ONLY those outputs
```

Default all six selected, preserving current behavior. At least one required.

This must be a **separate UI panel** from experimental CLAP `Instrumentação sugerida`: CLAP checkboxes are advisory observations, NOT requested audio outputs.

Show user-facing help text: "No Core Stems, escolher menos faixas economiza arquivos no disco, mas normalmente não acelera o cálculo da IA."

If a user requests Strings/Synth/Lead Guitar/Backing Vocals etc., don't offer them as available stem checkboxes until there is an approved separator. The experimental detector remains optional and never blocks Core Stems.

## Device policy

Extend existing `DevicePolicy` in a backwards-compatible way:
- `CUDA_REQUIRED` ("cuda"): must use NVIDIA CUDA; fail explicitly if unavailable; never fall back.
- `CPU_REQUIRED` ("cpu"): **force** the entire job to use CPU, including on a PC that has NVIDIA installed; validate actual selected device.
- `AUTO` ("auto"): choose CUDA if available, CPU otherwise; report chosen device clearly and do **not** silently fall back to CPU after a CUDA runtime error/OOM.

UI device menu:
- "Automático (GPU NVIDIA, senão CPU)" — default for new users;
- "GPU NVIDIA (CUDA)";
- "CPU (mais lento)".

A visible warning must appear before/during CPU execution; GPU absence must not block starting. No invented per-song ETA.

Implementation:
- Propagate policy `UI → JobLaunch → versioned worker args → build_request → SeparationService → AudioSeparatorBackend → manifest`.
- `CPU_REQUIRED` must be forced before Torch/device initialization in the **separate worker process**, e.g. by setting `CUDA_VISIBLE_DEVICES=-1` in the job process environment or equivalent robust mechanism verified for the pinned version.
- The parent UI must NOT import Torch for device selection.
- Disable autocast in effective CPU runs: FP32; preserve current CUDA behavior.
- `AUTO` may preflight capability inside worker, then select one concrete policy. On GPU inference errors do not retry CPU automatically.
- Validate `effective_device == cpu` for CPU_REQUIRED and `== cuda` for CUDA_REQUIRED.
- Keep single heavy model at a time and no GPU requirements in the general GUI startup.
- Existing CPU-capable `torch==2.8.0+cu128` is preferred; no global CUDA/driver/Python changes.
- Some very old processors may fail to support the pinned Torch runtime or lack RAM. Do not claim support for *every* Pentium before testing on one.

CLAP instrument analysis can remain CUDA-only for now. On CPU-only hosts it must show a clear non-blocking explanation (e.g. "Análise automática indisponível em CPU nesta versão") rather than making separation fail. CPU separation must be fully usable without CLAP.

## Requested stem selection

Canonical allowed selection for `Core Stems`:
`vocals, drums, bass, guitar, piano, other`.

Transport the canonical target IDs through a serializable worker contract, independent of CLAP confirmations. Reject:
- no selection;
- invalid target IDs;
- duplicate IDs;
- mixed pipeline IDs;
- paths supplied in place of stem names.

Compatibility: existing headless calls and tests that do not pass selected targets still mean **all six**.

Recommended simplest safe implementation for this checkpoint:

1. Run the exact already-validated Core 6-stem model once.
2. Validate its six outputs under existing engine contracts.
3. Keep only requested files. Do not leave unselected stem files in the final directory.
4. Return/serialize only selected stems to the UI and final manifest; record `requested_roles` and `produced_roles` without lying about how many roles were inferred.
5. Never delete the requested outputs or input on an error. Keep failures recoverable.
6. The selection doesn't need `output_single_stem` optimization for this checkpoint. Prefer reliable post-filtering over an invasive backend change.
7. Never re-run Core for each selected target.

Any post-filter/prune should happen in the service/application layer after validation and before final success manifest. Use canonical paths under the job's output directory only. Never delete arbitrary user paths. Preserve input immutability and model hash checks.

## Player + exports

The existing `MultiStemPlayer` supports an arbitrary stem mapping. The UI should populate it with exactly the returned requested stem subset.

- One selected stem: one playable stem row.
- Two selected stems: exactly two rows.
- Export one/all: only requested outputs.
- A/B Original↔Stems stays exclusive. Label or hint must clarify "Stems selecionados" are not a complete reconstruction of the song if fewer than six were selected.
- New music/analysis/reset states must not unexpectedly rewrite the deliberate selection.

## CPU-specific diagnostics

Current `scripts/doctor.py` **hard-requires RTX 5060 and CUDA**. Extend diagnostics to support `--profile cpu` (and preserve existing GPU profile/default for the user's validated rig).

CPU profile must:
- verify local Python, PyTorch CPU tensors, FFmpeg, audio-separator, player dependencies, Core checkpoint/hash and local project paths;
- not require `nvidia-smi`, CUDA tensor, RTX 5060, CLAP detector or research specialist checkpoints;
- report missing optional GPU/detector artifacts as nonblocking or not applicable;
- fail meaningfully for missing Core artifacts, broken dependency versions or failed CPU tensor operations.

Do not silently downgrade the existing GPU profile. CPU-only startup and separate operation should not call GPU-only doctor prechecks.

## Validation

Core tests:
- `DevicePolicy` serialization and worker args for `auto/cuda/cpu`;
- default behavior unchanged;
- forced CPU on a CUDA-equipped host really resolves to CPU;
- AUTO without CUDA → CPU (explicit, visible);
- CUDA_REQUIRED without CUDA → recoverable failure and no CPU fallback;
- GPU failure/OOM in AUTO does not silently retry CPU;
- CPU autocast disabled, effective precision FP32;
- six Core outputs still validated before subset retention;
- target subset validation including duplicates, unknown and empty;
- Core model inference called once for any subset;
- unselected stems do not remain on disk and do not appear in final manifest;
- only selected stems appear in player/export;
- input SHA-256 intact; UTF-8 paths;
- selection must be independent of CLAP analysis panel;
- safe cleanup never deletes paths outside output_dir.

Gates:
- `pytest -q`;
- `pip check`;
- `doctor.py` current GPU profile;
- `doctor.py --profile cpu`;
- GPU smoke with all 6 roles (regression);
- opt-in CPU smoke on a short synthetic/real licensed fixture using pinned BS-RoFormer SW;
- opt-in GPU smoke selected subset;
- player/export UI smoke selected subset;
- runtime wall time, peak RAM where possible and effective device in report.

Manual gate:
- On RTX 5060: choose CPU explicitly, run short file, verify manifest says cpu/FP32.
- On RTX 5060: GPU all six still works and player/export unchanged.
- With `CUDA_VISIBLE_DEVICES=-1` inherited in worker (or on a truly GPU-less PC): automatic choice actually uses CPU.
- Core "Bass + Guitar" -> only Bass and Guitar exist/show/export.
- Single "Vocals" -> only Vocals exists/show/export.
- Clarify CPU performance is hardware-dependent; do not promise Pentium times until measured.

## Scope exclusions

No new models, no CUDA/torch/library upgrades, no install-global operations, no detector training or calibration, no specialist integration, no multi-model orchestration, no new audio DSP processing, no permission to change supply-chain rules, no database/server/DAG, no batch, no waveform or theme redesign.

**Do not report Checkpoint 4 PASS until the code and tests really execute locally.**
