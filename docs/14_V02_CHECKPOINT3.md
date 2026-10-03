# StemLab v0.2 — Checkpoint 3: Specialist Quality Gate (Guitar + Bass)

**Status:** technical PASS; manual quality gate pending

O harness, a allowlist local e os smokes CUDA/offline foram concluídos em
2026-10-02. Isso não aprova qualidade nem promove especialistas; veja
`docs/generated/v02-checkpoint3-technical-report.md` e execute o gate humano em
`bench/README_SPECIALIST_GATE.md`.

**Goal:** stop spending product effort on metadata-only detection and prove, with real audio, whether specialist MSS stages materially improve the two problems already heard by the user: mixed/muddy guitars and weak/contaminated bass.

This checkpoint is a **quality gate**, not a production promotion. No specialist becomes a default merely because it loads or produces files.

## Why this checkpoint exists

Checkpoint 2 proved the analysis/process architecture but failed its manual musical quality gate: on a known track with clearly audible guitar, the CLAP detector returned guitar as not suggested and confused neighboring categories. Keep that detector advisory/experimental only.

The current Core Stems output is still BS-RoFormer SW and the user has already heard:
- multiple guitars collapsed into one Guitar stem;
- pad/keys bleed in Guitar on some material;
- Bass lacking definition / carrying unwanted material.

The next useful question is therefore: **do available local specialists audibly improve those outputs?**

## Public evidence guiding the experiment

Current MVSep behavior provides two useful hypotheses:
- its Lead/Rhythm Guitar algorithm exposes a two-stage variant as the default and reports SDR 9.21 versus 9.02 for one-stage;
- its Bass page reports BS-RoFormer SW at 14.62 SDR and an SCNet XL + BS-RoFormer SW ensemble at 14.87 on its own evaluation.

These numbers are only directional. Different datasets/protocols are not directly comparable to StemLab and do not promote any model by themselves.

## Pinned research candidates

Installed only through `scripts/install_specialist_candidates.py`.

### G1/G2 — Lead/Rhythm candidate

- id: `lead_rhythm_listra92`
- architecture: Mel-Band Roformer
- task: Lead / Rhythm Guitar
- source mirror: `noblebarkrr/mvsepless_resources`
- immutable revision: `2749bf2dcd4d04f019c0581c49cb8891d77fddb4`
- checkpoint: `mbr_lead_rhythm_guitar_listra92.ckpt`
- bytes: `337073664`
- checkpoint SHA-256: `b3c47bca33609ca1ba0bb2d2076410bfd1eb941b051b72afc1f3e24d12b17eef`
- expected stems from config: Lead, Rhythm
- license/redistribution: **unknown; research-only**

Do not claim this is the same weight used by the MVSep hosted Lead/Rhythm service.

### B1 — Bass candidate

- id: `bass_xlancer`
- architecture: BS Roformer
- task: Bass / Other
- source mirror: `noblebarkrr/mvsepless_resources`
- immutable revision: `4e97e0fec0e787df4573cd8cb68a5a8d216dc120`
- checkpoint: `bs_bass_xlancer.ckpt`
- bytes: `204411168`
- checkpoint SHA-256: `c409465e3dccfd83fa34e6a807dbdae2f4f1db24f2f85a0fdc146b6fa828afff`
- expected stems from config: bass, other
- license/redistribution: **unknown; research-only**

## Required experiments

For each private user track used in the gate, generate:

### Guitar

**G0 — baseline**
- existing BS-RoFormer SW Core Stems Guitar output.

**G1 — specialist direct**
- original full mix -> `lead_rhythm_listra92` -> Lead + Rhythm.

**G2 — two-stage**
- original full mix -> current BS-RoFormer SW Core Stems -> Guitar;
- Guitar stem -> `lead_rhythm_listra92` -> Lead + Rhythm.

The purpose is to test whether pre-filtering the mix helps the role-aware specialist, not to assume that it does.

### Bass

**B0 — baseline**
- existing BS-RoFormer SW Core Stems Bass output.

**B1 — specialist direct**
- original full mix -> `bass_xlancer` -> Bass.

No bass ensemble in this checkpoint. First establish whether one specialist clearly beats the current baseline perceptually.

## Output organization

Research outputs live under `bench/private/` and never enter Git.

Use a deterministic human-friendly layout similar to:

```text
bench/private/<track>/<run>/
  manifest.json
  guitar/
    G0_core_guitar.wav|flac
    G1_direct_lead.wav|flac
    G1_direct_rhythm.wav|flac
    G2_twostage_lead.wav|flac
    G2_twostage_rhythm.wav|flac
  bass/
    B0_core_bass.wav|flac
    B1_specialist_bass.wav|flac
```

The manifest records:
- input path + SHA-256;
- model/checkpoint/config hashes;
- pipeline variant;
- runtime;
- effective device/precision;
- peak CUDA allocated/reserved;
- output metadata and hashes;
- warnings/errors.

Do not normalize individual research outputs.

## Integration architecture

Reuse the existing `SeparationService -> SeparationBackend -> AudioSeparatorBackend` seam and the pinned `audio-separator==0.47.0`.

The specialist files are intentionally not arbitrary user-imported models.

If `audio-separator`'s normal registry cannot resolve the local candidate filenames, implement the smallest safe resolver inside StemLab's adapter layer:

- only exact candidate IDs in an internal allowlist;
- exact verified checkpoint + config paths/hashes;
- no network access during inference;
- no modification of site-packages;
- no generic "open any .ckpt/.pth";
- preserve the normal existing path for Core Stems;
- inspect the installed 0.47.0 loader contract before overriding anything;
- if a narrow subclass/override of model resolution is used, test the exact tuple/config contract so future library drift fails loudly.

One heavy model at a time. Release model/process/CUDA resources between stages.

## Research harness

Create a headless command for the gate, for example:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_specialists.py --input "C:\path\song.wav"
```

Exact CLI naming may follow existing project conventions, but the behavior must be deterministic and non-interactive.

It should:
1. verify specialist receipt/hashes before any model load;
2. preserve input hash;
3. run Core once and reuse G0/B0;
4. run G1;
5. run G2 using G0 as input;
6. run B1;
7. unload between heavy stages;
8. write manifest and concise console summary;
9. work with network unavailable.

A failed variant must be reported clearly; do not silently substitute another model.

## Automated validation

Technical PASS requires:

- specialist installer `--verify-only` PASS;
- config hashes from the installed immutable revision are pinned in project code/docs before model load;
- full test suite remains green;
- current BS-RoFormer SW Core smoke remains green;
- both specialist candidates load on the RTX 5060 and produce the expected roles;
- output duration/sample rate/channels/finiteness are valid;
- input is byte-identical;
- offline inference passes;
- runtime + peak VRAM recorded per stage;
- sequential stages do not retain a conflicting CUDA allocation into the next process/stage;
- G0/B0 are reused rather than rerunning Core separately;
- research outputs remain under ignored `bench/private/`;
- no CLAP decision is required to run the benchmark.

Synthetic/short fixtures establish software correctness only, not audio quality.

## Manual quality gate

Automated PASS is insufficient.

The user should run the harness on **at least three songs they know well**, preferably including:
- simultaneous lead/rhythm guitars;
- sections with one guitar alone and both together;
- clean and/or distorted guitars;
- a song where pad/keys previously leaked into Guitar;
- bass interacting with kick and low guitars/keys.

Listen primarily for:

### Guitar
- Lead/Rhythm semantic stability;
- whether both guitars remain collapsed;
- cross-bleed;
- pad/keys/vocals leakage;
- watery/metallic artifacts;
- transient attack;
- sustain/reverb preservation.

Compare G1 vs G2 as well as both against G0.

### Bass
- definition/attack;
- kick leakage;
- low guitar/keys/synth leakage;
- fullness/body;
- musical artifacts.

Compare B1 directly against B0.

## Gate outcomes

Each task gets one of:

- `approved_for_integration`
- `experimental_continue`
- `rejected`

Do not promote based on one song.

If Guitar G2 is consistently better, the next implementation checkpoint may add Guitar Lab to the real app.
If G1 wins instead, integrate direct specialist routing.
If neither wins clearly, reject this candidate and benchmark another.
The same logic applies to B1 versus B0.

## Explicitly out of scope

- production UI integration of Lead/Rhythm or Bass HQ;
- replacing Core Stems;
- detector/CLAP calibration;
- automatic detector-driven routing;
- bass ensemble;
- synth/keys/strings specialists;
- Lead/Backing vocals;
- SATB;
- DrumSep;
- training/fine-tuning;
- generic model registry/importer;
- packaging/release.
