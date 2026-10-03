# audio-separator 0.47.0 — Lead/Rhythm loader inspection

**Inspected:** installed `audio-separator==0.47.0` distribution in the project `.venv`.

## Question

Why does the verified `lead_rhythm_listra92` checkpoint fail to load even though
its pinned YAML declares `mlp_expansion_factor: 2`?

## Finding

`ConfigurationNormalizer` preserves the value `2`, and `RoformerLoader` passes it
to `MelBandRoformer`. In the vendored implementation, however,
`MelBandRoformer.__init__` constructs each `MaskEstimator` without forwarding the
argument. `MaskEstimator` therefore uses its default `4`. For model dimension
384, the loader creates hidden layers of 1536 while the checkpoint contains the
expected 768-wide layers. `load_state_dict` then fails with deterministic size
mismatches.

Relevant installed files:

- `audio_separator/separator/roformer/configuration_normalizer.py`
- `audio_separator/separator/roformer/roformer_loader.py`
- `audio_separator/separator/uvr_lib_v5/roformer/mel_band_roformer.py`

## Local resolution

StemLab does not modify `site-packages`, the YAML, or the checkpoint. Its adapter
uses a candidate-specific `RoformerLoader` subclass only for the exact
`lead_rhythm_listra92` allowlist tuple. Before the state dict is loaded, it
rebuilds the still-empty mask estimators with the already-normalized expansion
factor. Core Stems and `bass_xlancer` continue through the unmodified loader.

This is a compatibility shim for the pinned dependency/candidate combination,
not a generic model importer. Removal should be reconsidered only after a future
dependency evaluation proves that the upstream loader propagates the parameter.
