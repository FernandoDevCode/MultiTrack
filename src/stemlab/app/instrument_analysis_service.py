from __future__ import annotations

from pathlib import Path
import time

from stemlab.app.audio_windows import FfmpegWindowDecoder, plan_analysis_windows
from stemlab.app.instrumentation import aggregate_instrument_evidence
from stemlab.audio import sha256_file
from stemlab.domain import InstrumentationAnalysisResult
from stemlab.instrumentation.backend import InstrumentDetector


class InstrumentationAnalysisService:
    def __init__(self, detector: InstrumentDetector, decoder: FfmpegWindowDecoder) -> None:
        self.detector = detector
        self.decoder = decoder

    def analyze(self, input_path: Path) -> InstrumentationAnalysisResult:
        started = time.perf_counter()
        source = input_path.resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        input_hash = sha256_file(source)
        duration = self.decoder.duration_seconds(source)
        windows = plan_analysis_windows(duration)
        decoded = tuple(self.decoder.decode(source, window) for window in windows)
        detector_result = self.detector.score_windows(decoded)
        if sha256_file(source) != input_hash:
            raise RuntimeError("Input audio changed during instrument analysis.")
        evidence = aggregate_instrument_evidence(detector_result.window_scores)
        return InstrumentationAnalysisResult(
            schema_version=1,
            input_path=source,
            input_sha256=input_hash,
            duration_seconds=duration,
            windows=windows,
            evidence=evidence,
            model_id=getattr(self.detector, "model_id", "instrument-detector"),
            model_revision=getattr(self.detector, "model_revision", "unknown"),
            effective_device=detector_result.effective_device,
            runtime_seconds=time.perf_counter() - started,
            peak_cuda_allocated_bytes=detector_result.peak_cuda_allocated_bytes,
            peak_cuda_reserved_bytes=detector_result.peak_cuda_reserved_bytes,
        )
