# StemLab v0.2 — Checkpoint 1: Core + Player

**Status:** **PASS** em 2026-10-02; evidências em `docs/generated/v02-checkpoint1-report.md`
**Goal:** turn the current separator into a usable local listening/export tool without yet adding automatic instrument detection or specialist models.

## Scope

Checkpoint 1 delivers:

1. current BS-RoFormer SW Core Stems path preserved and stable;
2. synchronized multistem player inside the app;
3. Solo / Mute / per-stem monitoring volume;
4. Play / Pause / Seek with one shared transport;
5. safe A/B between Original and the stem mix;
6. export one stem or all stems without re-encoding;
7. extract audio from a video with the project-local FFmpeg;
8. a minimal processing-plan/router seam for future adaptive pipelines.

Checkpoint 1 does **not** add:

- instrument detection / CLAP;
- specialist Bass/Guitar/Vocal models;
- Lead/Rhythm;
- Lead/Backing;
- SATB;
- ensembles;
- waveform/spectrogram;
- generic model registry/downloader;
- database/server/cloud;
- batch queue.

## Product behavior

### Main flow

```text
Open media
   ↓
Core Stems
   ↓
BS-RoFormer SW
   ↓
result session
   ↓
Original + stems available in one synchronized player
```

The UI should stop presenting "6 stems" as the identity of the product. The current general pipeline is labeled **Core Stems**. It still yields the six BS-RoFormer SW roles internally at this checkpoint.

### Player

After a successful separation, show one row per stem:

```text
Vocals   [M] [S] ── volume ── [Export]
Drums    [M] [S] ── volume ── [Export]
Bass     [M] [S] ── volume ── [Export]
Guitar   [M] [S] ── volume ── [Export]
Piano    [M] [S] ── volume ── [Export]
Other    [M] [S] ── volume ── [Export]
```

Transport:

- Play / Pause;
- shared seek;
- current time / duration;
- one shared sample/frame position for all stems.

Mixer semantics:

- with no Solo active: all non-muted stems are monitored;
- with one or more Solo active: only soloed, non-muted stems are monitored;
- volume changes monitoring only, never the files;
- Original A/B is exclusive: Original and stem mix must never be summed together accidentally.

No independent media players per stem. That would permit drift and is not acceptable.

### Playback implementation

Use a streaming player, not "load the whole song into RAM".

Preferred implementation for this checkpoint:

- `soundfile` for reading WAV/FLAC stem streams;
- `sounddevice==0.5.6` for one shared Windows output stream;
- `numpy` for block mixing;
- UI polls lightweight playback state through a timer; audio callback does not manipulate widgets.

`sounddevice 0.5.6` is the only new runtime dependency expected for this checkpoint.

Player must fail recoverably if the audio output device cannot be opened; separation/export must continue to work.

### Original A/B

The input may be MP3/AAC/M4A or another format not suitable for direct `soundfile` streaming.

For reliable A/B:

- create a local lossless monitor copy/decoded cache through the existing local FFmpeg when needed;
- keep it under the run/workspace, never beside/over the source file;
- do not modify the original;
- do not introduce a lossy intermediate.

### Export

"Export" means file delivery, not DSP.

- Export one stem: copy the already-created WAV/FLAC byte-for-byte to a user-selected destination.
- Export all: copy all result stems to a new destination folder.
- Never silently overwrite.
- Do not normalize, transcode, resample or change gain during export.
- The source result files remain intact.

### Extract audio from video

Add a small separate action, **Extrair áudio de vídeo…**

Supported input for this checkpoint: common local video containers (MP4, MKV, MOV, WebM, AVI, M4V).

Output:

- FLAC or WAV;
- local FFmpeg only;
- first audio stream only for this checkpoint;
- no video;
- no silent overwrite;
- preserve sample rate/channels unless FFmpeg requires otherwise;
- WAV uses lossless PCM; FLAC uses FLAC;
- run with QProcess/list arguments, never `shell=True`;
- validate output as real audio before reporting success;
- source video remains byte-identical.

### Minimal router seam

Do not build a generic DAG engine.

Introduce only enough domain/application structure so the UI asks for a **pipeline/preset**, not directly for a third-party model.

For Checkpoint 1:

```text
Core Stems
  -> one SeparationStep
  -> existing SIX_STEMS / BS-RoFormer SW
```

The resulting plan must be serializable/plain data and leave a clear place for Checkpoint 2 to insert analysis/routing and later specialist steps.

The existing permanent seam remains:

```text
SeparationService -> SeparationBackend -> AudioSeparatorBackend
```

Do not bypass it.

## Performance constraints

- one heavy model at a time;
- no full-song multi-stem preload into RAM;
- player must not hold CUDA resources;
- closing/replacing a result must release all audio handles;
- UI must remain responsive during FFmpeg extraction and separation.

## Validation gate

Checkpoint 1 is PASS only if:

- existing BS-RoFormer SW GPU smokes still pass;
- existing tests pass;
- player loads a six-stem result;
- Play/Pause/Seek share one timeline;
- Solo/Mute semantics have deterministic tests;
- volume is monitoring-only;
- Original A/B never doubles original + stems;
- stream implementation does not preload complete tracks;
- export-one is byte-identical;
- export-all copies the complete stem set without silent overwrite;
- FFmpeg video->WAV/FLAC smoke produces valid audio and leaves source unchanged;
- UI stays responsive;
- `pip check` and `scripts/doctor.py` pass;
- no model, source audio, output or cache is committed.

## Manual acceptance

After automated PASS, the user should be able to:

1. launch `START-STEMLAB.bat`;
2. separate a normal song with Core Stems;
3. press Play in-app;
4. Solo Guitar, then Bass;
5. seek to another point without tracks drifting;
6. switch A/B between Original and stem mix;
7. export Guitar only;
8. export all stems;
9. extract FLAC/WAV from one video.

This checkpoint does not claim improved source-separation quality beyond the already validated BS-RoFormer SW.
