from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from stemlab.audio import MultiStemPlayer, sha256_file


class FakeOutputStream:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def abort(self) -> None:
        self.started = False

    def close(self) -> None:
        self.closed = True


def _audio(path: Path, value: float, *, frames: int = 1000, rate: int = 1000) -> Path:
    subtype = "PCM_24" if path.suffix.lower() == ".flac" else "FLOAT"
    sf.write(path, np.full((frames, 2), value, dtype=np.float32), rate, subtype=subtype)
    return path


def test_one_stream_play_pause_seek_and_shared_cursor(tmp_path: Path) -> None:
    streams = []

    def factory(**kwargs):
        stream = FakeOutputStream(**kwargs)
        streams.append(stream)
        return stream

    player = MultiStemPlayer(stream_factory=factory, blocksize=64)
    player.load_session(
        {"vocals": _audio(tmp_path / "vocals.wav", 0.1), "drums": _audio(tmp_path / "drums.wav", 0.2)},
        original=_audio(tmp_path / "original.wav", 0.75),
    )
    player.play()
    assert len(streams) == 1
    assert streams[0].kwargs["channels"] == 2
    assert player.state().playing
    block = player.render_block(64)
    np.testing.assert_allclose(block, 0.3, atol=1e-6)
    assert player.state().frame == 64
    player.pause()
    assert not player.state().playing
    player.seek(0.5)
    assert player.state().frame == 500
    player.play()
    assert len(streams) == 1
    player.close()
    assert streams[0].closed


def test_mute_solo_multiple_solo_volume_and_ab_are_exact(tmp_path: Path) -> None:
    vocals = _audio(tmp_path / "vocals.flac", 0.1)
    drums = _audio(tmp_path / "drums.flac", 0.2)
    bass = _audio(tmp_path / "bass.flac", 0.3)
    hashes = {path: sha256_file(path) for path in (vocals, drums, bass)}
    player = MultiStemPlayer(stream_factory=FakeOutputStream)
    player.load_session(
        {"vocals": vocals, "drums": drums, "bass": bass},
        original=_audio(tmp_path / "original.flac", 0.75),
    )

    np.testing.assert_allclose(player.render_block(8), 0.6, atol=2e-4)
    player.seek(0)
    player.set_mute("bass", True)
    np.testing.assert_allclose(player.render_block(8), 0.3, atol=2e-4)
    player.seek(0)
    player.set_solo("vocals", True)
    player.set_solo("drums", True)
    np.testing.assert_allclose(player.render_block(8), 0.3, atol=2e-4)
    player.seek(0)
    player.set_mute("drums", True)
    player.set_volume("vocals", 0.5)
    np.testing.assert_allclose(player.render_block(8), 0.05, atol=2e-4)
    player.seek(0)
    player.set_mode("original")
    np.testing.assert_allclose(player.render_block(8), 0.75, atol=2e-4)
    assert {path: sha256_file(path) for path in hashes} == hashes
    player.close()


def test_render_reads_only_requested_blocks_not_complete_track(tmp_path: Path) -> None:
    player = MultiStemPlayer(stream_factory=FakeOutputStream)
    player.load_session({"vocals": _audio(tmp_path / "long.wav", 0.1, frames=50_000)})
    assert player.state().frame == 0
    assert player.render_block(127).shape == (127, 2)
    assert player.state().frame == 127
    assert player.state().total_frames == 50_000
    player.close()
