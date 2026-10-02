# StemLab v0.2 — Checkpoint 2: Instrument Analysis + Adaptive Planning

**Status:** technical **PASS** em 2026-10-02; quality/manual gate pendente; evidências em `docs/generated/v02-checkpoint2-report.md`

**Goal:** add an advisory local music-instrument analysis layer and make pipeline planning target-aware without yet adding specialist separation models.

## Product boundary

Checkpoint 2 answers:

> "What instrumentation is probably present in this track, and what can StemLab currently do with it?"

It does **not** claim:

> "Every detected instrument can already be isolated."

Detection and separation are separate capabilities.

## Detector

Approved detector:

- model: `laion/larger_clap_music`
- architecture: CLAP
- license declared by model card: Apache-2.0
- immutable revision: `a0b4534a14f58e20944452dff00a22a06ce629d1`
- weight: `pytorch_model.bin`
- expected bytes: `776444665`
- expected SHA-256: `5c289311f4a030d768af7ffbfdecd01b008aa64824211899a4e59f4f9d154fd1`

The model is installed separately by:

```powershell
.\.venv\Scripts\python.exe scripts\install_instrument_detector.py
```

and must pass:

```powershell
.\.venv\Scripts\python.exe scripts\install_instrument_detector.py --verify-only
```

before implementation/inference.

Runtime loading must use only the verified local directory, with network disabled/local-only semantics and no remote code.

## Dependency budget

One direct runtime dependency is approved:

- `transformers==5.18.0`

Its normal transitive dependencies are allowed.

Do not add `datasets`, `accelerate`, TensorFlow, Essentia, musicnn or another detector stack unless a blocker is demonstrated.

## Analysis execution

Heavy analysis runs outside the UI process.

Target seam:

```text
UI
  -> QProcess analysis worker
  -> InstrumentationAnalysisService
  -> InstrumentDetector protocol
  -> ClapInstrumentDetector
  -> verified local larger_clap_music
```

Domain/application contracts must not import PySide6 or Torch.

The analysis worker should exit after producing its result so CUDA/VRAM is released before source separation begins.

No silent CPU fallback. If CUDA is required and unavailable, return a recoverable structured error.

## Audio sampling

CLAP accepts 10-second 48 kHz windows. Analyze representative windows instead of loading the whole song into the model.

Rules:

- use the existing local FFmpeg/FFprobe;
- decode only analysis windows;
- mono float32 at 48 kHz;
- no lossy intermediate;
- no modification of source;
- at most 8 windows;
- for tracks <=10 seconds: one window;
- otherwise space windows deterministically across the valid duration;
- no random truncation;
- never load the whole decoded song into RAM merely for analysis.

## Curated taxonomy

Checkpoint 2 uses a small canonical taxonomy. Internal CLAP prompts are English; UI labels are user-facing.

Canonical targets:

- vocals
- drums
- bass
- guitar
- piano
- keys
- synth_pad
- organ
- percussion
- strings
- brass
- woodwind
- choir

Each canonical target may have 2–4 fixed prompt aliases. Example: `synth_pad` may compare against "synthesizer pad", "synth pad", and "electronic synthesizer".

Do not expose arbitrary user text prompts in this checkpoint.

Do not claim instrument counts. In particular, detection of `guitar` does **not** mean the model knows whether there is one guitar or several.

## Evidence semantics

CLAP similarity is **not a calibrated probability**.

Do not display "97% confidence".

For each canonical target record enough evidence to review the result, such as:

- aggregate similarity;
- peak similarity;
- number of sampled windows where the target ranked strongly;
- a state like `suggested`, `possible`, or `not_suggested`.

Use deterministic ranking/aggregation rules and test them.

The UI must communicate that these are **suggestions**.

## User confirmation

After analysis, show an editable instrumentation panel.

Example:

```text
Instrumentação sugerida

[x] Vocals
[x] Drums
[x] Bass
[x] Guitar
[ ] Piano
[x] Synth / Pad
[ ] Strings
...

Sugestão automática — confirme/corrija antes de separar.
```

The user can add/remove any canonical target before planning.

The confirmed selection, not the raw detector output, is the source of truth for the requested targets.

## Adaptive plan

Extend the existing `PipelinePlan` minimally. Do not create a generic DAG engine.

The planner receives confirmed targets and returns a serializable plan/capability report.

Current capability mapping:

- vocals -> Core Stems / vocals
- drums -> Core Stems / drums
- bass -> Core Stems / bass
- guitar -> Core Stems / guitar
- piano -> Core Stems / piano
- keys -> no specialist yet
- synth_pad -> no specialist yet
- organ -> no specialist yet
- percussion -> no specialist yet
- strings -> no specialist yet
- brass -> no specialist yet
- woodwind -> no specialist yet
- choir -> no specialist yet

If any available Core target is requested, run Core Stems **once**, never once per target.

Unsupported specialist targets must be explicit in the plan/UI, e.g. "Detectado, separador especializado ainda não instalado". Do not pretend `other` is a clean synth/strings/etc. separation.

At this checkpoint the actual MSS execution remains BS-RoFormer SW Core Stems. This checkpoint prepares routing; it does not add quality-specialist stages.

## UI

Keep one main screen.

Add:

- `Analisar instrumentos` action for the selected track;
- analysis progress/status;
- editable suggested instrumentation list;
- clear distinction between:
  - available through Core Stems;
  - detected but requiring a future specialist;
- re-analyze action.

Do not make analysis mandatory to use Core Stems. The user can still separate directly.

Do not add waveform or multi-tab project UI.

## Security/offline

- no audio upload;
- no telemetry;
- no remote inference;
- after detector + dependencies are installed, analysis must work with network unavailable;
- use `local_files_only=True` or equivalent;
- `trust_remote_code=False`;
- model artifacts must match installer receipt before load;
- source audio remains read-only;
- no arbitrary checkpoints/prompts.

## Validation

Automated PASS requires:

- existing Checkpoint 1 tests remain healthy;
- detector installer `--verify-only` PASS;
- local CLAP load from verified directory;
- CUDA effective, with runtime/peak VRAM recorded;
- process exits and CUDA memory is released before separation smoke;
- 10-second-window sampling is deterministic and capped at 8;
- input hash unchanged;
- structured analysis result serializes cleanly;
- no probability wording;
- user overrides change the plan deterministically;
- Core targets collapse to one Core Stems pass;
- unsupported targets are reported, not silently mapped to `other`;
- analysis works offline after setup;
- UI stays responsive during analysis;
- full test suite, `pip check`, `doctor.py` PASS.

## Quality/manual gate

Synthetic tests cannot prove instrument-recognition quality.

After technical PASS, manual validation is required on at least a few real songs whose instrumentation the user broadly knows. Evaluate:

- obvious instruments detected;
- false positives;
- instruments present only in one section;
- synth/pad vs piano/keys ambiguity;
- guitar presence (not guitar count).

Checkpoint 2 can be technically PASS while the detector remains labeled experimental/advisory until the user's listening/knowledge check is satisfactory.

## Out of scope

- Lead/Rhythm separation;
- multiple-guitar counting/separation;
- Bass HQ;
- Lead/Backing vocals;
- SATB;
- specialist synth/keys/strings/brass/woodwind models;
- AudioSep;
- Mega 53-stem;
- ensembles;
- training/fine-tuning;
- generic model manager/registry;
- automatic model download from UI.
