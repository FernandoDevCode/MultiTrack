from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf
from audio_separator.separator.common_separator import CommonSeparator

from stemlab.audio import sha256_file
from stemlab.domain import OutputFormat
from stemlab.separation.audio_separator_adapter import AudioSeparatorBackend


def _writer(tmp_path: Path, output_format: OutputFormat) -> CommonSeparator:
    return CommonSeparator({
        "logger": logging.getLogger(__name__), "log_level": logging.ERROR,
        "model_name": "fixture", "model_path": "fixture", "model_data": {},
        "output_dir": str(tmp_path), "output_format": output_format.value,
        "sample_rate": 44100, "normalization_threshold": 1.0,
        "amplification_threshold": 0.0, "use_soundfile": True,
    })


@pytest.mark.parametrize("output_format,expected_subtype", [
    (OutputFormat.WAV, "FLOAT"), (OutputFormat.FLAC, "PCM_24"),
])
def test_real_mp3_input_can_be_written_to_pcm_container(
    tmp_path: Path, output_format: OutputFormat, expected_subtype: str,
) -> None:
    samples = np.column_stack([
        np.sin(np.arange(4410) * .1) * .2,
        np.cos(np.arange(4410) * .1) * .1,
    ]).astype("float32")
    source = tmp_path / "música [entrada].mp3"
    sf.write(source, samples, 44100, format="MP3")
    before = sha256_file(source)
    decoded, rate = sf.read(source, dtype="float32", always_2d=True)
    model = _writer(tmp_path, output_format)
    # The actual upstream input inspection feeding the output writer.
    model.prepare_mix(str(source))
    model.audio_file_path = str(source)
    assert model.input_subtype == "MPEG_LAYER_III"
    target = tmp_path / f"guitarra.{output_format.value.lower()}"
    separator = SimpleNamespace(model_instance=model)
    original_writer = model.write_audio_soundfile

    with AudioSeparatorBackend._compatible_soundfile_output(separator, output_format):
        model.write_audio(str(target), decoded * .5)

    info = sf.info(target)
    actual, actual_rate = sf.read(target, dtype="float32", always_2d=True)
    assert info.subtype == expected_subtype
    assert actual_rate == rate == 44100
    assert actual.shape == decoded.shape
    assert np.isfinite(actual).all()
    np.testing.assert_allclose(actual, decoded * .5, atol=2 ** -23, rtol=0)
    assert sha256_file(source) == before
    assert model.input_subtype == "MPEG_LAYER_III"
    assert model.write_audio_soundfile == original_writer
    assert not list(tmp_path.glob("*.partial"))


@pytest.mark.parametrize("output_format,source_subtype,expected", [
    (OutputFormat.WAV, "PCM_24", "PCM_24"),
    (OutputFormat.WAV, "FLOAT", "FLOAT"),
    (OutputFormat.FLAC, "PCM_16", "PCM_16"),
    (OutputFormat.FLAC, "FLOAT", "PCM_24"),
    (OutputFormat.WAV, "VORBIS", "FLOAT"),
])
def test_encoding_policy_preserves_supported_subtypes(
    tmp_path: Path, output_format: OutputFormat, source_subtype: str, expected: str,
) -> None:
    model = _writer(tmp_path, output_format)
    model.input_subtype = source_subtype
    target = tmp_path / f"stem.{output_format.value.lower()}"
    source = tmp_path / "input.wav"
    sf.write(source, np.ones((100, 2), dtype="float32") * .25, 44100)
    model.audio_file_path = str(source)
    with AudioSeparatorBackend._compatible_soundfile_output(
        SimpleNamespace(model_instance=model), output_format
    ):
        model.write_audio(str(target), np.ones((100, 2), dtype="float32") * .125)
    assert sf.info(target).subtype == expected
    assert model.input_subtype == source_subtype


def test_writer_state_restored_after_export_error(tmp_path: Path, monkeypatch) -> None:
    model = _writer(tmp_path, OutputFormat.WAV)
    model.input_subtype = "MPEG_LAYER_III"
    def fail(*_args):
        assert model.input_subtype == "FLOAT"
        raise OSError("disk full")
    monkeypatch.setattr(model, "write_audio_soundfile", fail)
    with pytest.raises(OSError, match="disk full"):
        with AudioSeparatorBackend._compatible_soundfile_output(
            SimpleNamespace(model_instance=model), OutputFormat.WAV
        ):
            model.write_audio_soundfile("stem.wav", np.zeros((10, 2)))
    assert model.write_audio_soundfile is fail
    assert model.input_subtype == "MPEG_LAYER_III"
