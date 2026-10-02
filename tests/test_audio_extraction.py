from __future__ import annotations

import os
from pathlib import Path
import subprocess

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication
import pytest

from stemlab.app.audio_extraction import ffmpeg_arguments, prepare_extraction
from stemlab.audio import sha256_file
from stemlab.workers.qprocess_audio import QProcessAudioExtraction


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def _video_fixture(repo_root: Path, path: Path) -> None:
    ffmpeg = repo_root / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    subprocess.run(
        [
            str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=32x32:d=0.2",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=0.2",
            "-shortest", "-c:v", "mpeg4", "-c:a", "aac", str(path),
        ],
        check=True,
    )


def test_extraction_command_is_argument_list_and_refuses_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"video")
    request = prepare_extraction(source, tmp_path / "audio.wav")
    arguments = ffmpeg_arguments(request)
    assert arguments[arguments.index("-map") + 1] == "0:a:0"
    assert "pcm_s24le" in arguments
    assert "-n" in arguments
    assert all("shell=True" not in argument for argument in arguments)
    request.output_path.write_bytes(b"occupied")
    with pytest.raises(FileExistsError):
        prepare_extraction(source, request.output_path)


@pytest.mark.parametrize("suffix", [".wav", ".flac"])
def test_qprocess_video_extraction_is_non_blocking_valid_and_input_safe(
    tmp_path: Path, qt_app, suffix: str
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = tmp_path / "fixture.mp4"
    _video_fixture(repo_root, source)
    source_hash = sha256_file(source)
    target = tmp_path / f"audio{suffix}"
    job = QProcessAudioExtraction(repo_root)
    completed, failures, heartbeats = [], [], []
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: heartbeats.append(1))
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    job.completed.connect(lambda metadata: (completed.append(metadata), loop.quit()))
    job.failed.connect(lambda message: (failures.append(message), loop.quit()))
    timer.start()
    timeout.start(10_000)
    job.start(source, target)
    assert job.running
    loop.exec()
    timer.stop()
    timeout.stop()
    assert not failures
    assert completed and completed[0].frames > 0
    assert target.is_file()
    assert sha256_file(source) == source_hash
    assert heartbeats, "QProcess bloqueou o event loop da UI"
