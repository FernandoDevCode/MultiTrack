from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
from typing import Callable

import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class PlaybackState:
    playing: bool
    frame: int
    total_frames: int
    sample_rate: int
    mode: str
    error: str | None

    @property
    def current_seconds(self) -> float:
        return self.frame / self.sample_rate if self.sample_rate else 0.0

    @property
    def duration_seconds(self) -> float:
        return self.total_frames / self.sample_rate if self.sample_rate else 0.0


@dataclass
class StemMonitorState:
    muted: bool = False
    soloed: bool = False
    volume: float = 1.0


def _default_stream_factory(**kwargs):
    import sounddevice as sd

    return sd.OutputStream(**kwargs)


class MultiStemPlayer:
    """One streaming transport and output stream shared by every monitored source."""

    def __init__(
        self,
        *,
        stream_factory: Callable[..., object] | None = None,
        blocksize: int = 2048,
    ) -> None:
        self._stream_factory = stream_factory or _default_stream_factory
        self._blocksize = blocksize
        self._lock = threading.RLock()
        self._stems: dict[str, sf.SoundFile] = {}
        self._original: sf.SoundFile | None = None
        self._monitor: dict[str, StemMonitorState] = {}
        self._stream = None
        self._frame = 0
        self._total_frames = 0
        self._sample_rate = 0
        self._channels = 0
        self._playing = False
        self._mode = "stems"
        self._error: str | None = None

    @property
    def roles(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._stems)

    def load_session(self, stems: dict[str, Path], *, original: Path | None = None) -> None:
        opened: list[sf.SoundFile] = []
        try:
            stem_handles = {role: sf.SoundFile(path.resolve(), mode="r") for role, path in stems.items()}
            opened.extend(stem_handles.values())
            original_handle = sf.SoundFile(original.resolve(), mode="r") if original else None
            if original_handle:
                opened.append(original_handle)
            if not stem_handles:
                raise ValueError("A sessão precisa de ao menos um stem.")
            reference = next(iter(stem_handles.values()))
            handles = list(stem_handles.values()) + ([original_handle] if original_handle else [])
            for handle in handles:
                if handle.samplerate != reference.samplerate or handle.channels != reference.channels:
                    raise ValueError("Todas as fontes monitoradas devem ter sample rate e canais iguais.")
            total_frames = min(handle.frames for handle in handles)
        except Exception:
            for handle in opened:
                handle.close()
            raise

        self.close()
        with self._lock:
            self._stems = stem_handles
            self._original = original_handle
            self._monitor = {role: StemMonitorState() for role in stem_handles}
            self._sample_rate = reference.samplerate
            self._channels = reference.channels
            self._total_frames = total_frames
            self._frame = 0
            self._mode = "stems"
            self._error = None

    def play(self) -> None:
        with self._lock:
            if not self._stems:
                raise RuntimeError("Nenhuma sessão de stems foi carregada.")
            if self._frame >= self._total_frames:
                self._seek_frame_locked(0)
            try:
                if self._stream is None:
                    self._stream = self._stream_factory(
                        samplerate=self._sample_rate,
                        channels=self._channels,
                        dtype="float32",
                        blocksize=self._blocksize,
                        callback=self._audio_callback,
                    )
                self._stream.start()
            except Exception as exc:
                self._playing = False
                self._error = str(exc)
                if self._stream is not None:
                    try:
                        self._stream.close()
                    except Exception:
                        pass
                    self._stream = None
                raise RuntimeError(f"Não foi possível abrir o dispositivo de áudio: {exc}") from exc
            self._error = None
            self._playing = True

    def pause(self) -> None:
        with self._lock:
            self._playing = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                except Exception as exc:
                    self._error = str(exc)

    def seek(self, seconds: float) -> None:
        with self._lock:
            frame = round(max(0.0, seconds) * self._sample_rate)
            self._seek_frame_locked(min(frame, self._total_frames))

    def set_mode(self, mode: str) -> None:
        if mode not in {"original", "stems"}:
            raise ValueError("O modo deve ser 'original' ou 'stems'.")
        with self._lock:
            if mode == "original" and self._original is None:
                raise RuntimeError("O original não está disponível para monitoramento.")
            self._mode = mode

    def set_mute(self, role: str, muted: bool) -> None:
        with self._lock:
            self._monitor[role].muted = bool(muted)

    def set_solo(self, role: str, soloed: bool) -> None:
        with self._lock:
            self._monitor[role].soloed = bool(soloed)

    def set_volume(self, role: str, volume: float) -> None:
        if not 0.0 <= volume <= 1.0:
            raise ValueError("Volume de monitoramento deve ficar entre 0 e 1.")
        with self._lock:
            self._monitor[role].volume = float(volume)

    def state(self) -> PlaybackState:
        with self._lock:
            return PlaybackState(
                playing=self._playing,
                frame=self._frame,
                total_frames=self._total_frames,
                sample_rate=self._sample_rate,
                mode=self._mode,
                error=self._error,
            )

    def render_block(self, frames: int) -> np.ndarray:
        """Render one block; public to permit deterministic device-free verification."""
        with self._lock:
            return self._render_block_locked(frames)

    def close(self) -> None:
        with self._lock:
            self._playing = False
            if self._stream is not None:
                try:
                    self._stream.abort()
                except Exception:
                    pass
                try:
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            for handle in list(self._stems.values()) + ([self._original] if self._original else []):
                handle.close()
            self._stems = {}
            self._original = None
            self._monitor = {}
            self._frame = 0
            self._total_frames = 0
            self._sample_rate = 0
            self._channels = 0

    def _audio_callback(self, outdata, frames, _time_info, status) -> None:
        with self._lock:
            if status:
                self._error = str(status)
            if not self._playing:
                outdata.fill(0)
                return
            outdata[:] = self._render_block_locked(frames)

    def _render_block_locked(self, frames: int) -> np.ndarray:
        output = np.zeros((frames, self._channels), dtype=np.float32)
        remaining = self._total_frames - self._frame
        read_frames = min(frames, max(remaining, 0))
        if read_frames <= 0:
            self._playing = False
            return output

        if self._mode == "original":
            sources = [(self._original, 1.0)] if self._original else []
        else:
            any_solo = any(state.soloed for state in self._monitor.values())
            sources = [
                (self._stems[role], state.volume)
                for role, state in self._monitor.items()
                if not state.muted and (not any_solo or state.soloed)
            ]
        for handle, gain in sources:
            if handle is None:
                continue
            handle.seek(self._frame)
            block = handle.read(read_frames, dtype="float32", always_2d=True)
            output[: len(block)] += block * gain
        self._frame += read_frames
        if self._frame >= self._total_frames:
            self._playing = False
        return output

    def _seek_frame_locked(self, frame: int) -> None:
        self._frame = frame
        for handle in list(self._stems.values()) + ([self._original] if self._original else []):
            handle.seek(frame)

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.close()
