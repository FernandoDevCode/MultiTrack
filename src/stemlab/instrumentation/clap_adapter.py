from __future__ import annotations

import gc
from pathlib import Path
from typing import Sequence

import numpy as np

from stemlab.app.instrumentation import PROMPT_ALIASES
from stemlab.instrumentation.backend import DetectorScoreResult
from stemlab.instrumentation.verification import verify_detector_artifacts


def load_local_clap(model_dir: Path, *, processor_cls=None, model_cls=None):
    if processor_cls is None or model_cls is None:
        from transformers import ClapModel, ClapProcessor

        processor_cls = processor_cls or ClapProcessor
        model_cls = model_cls or ClapModel
    common = {
        "local_files_only": True,
        "trust_remote_code": False,
    }
    processor = processor_cls.from_pretrained(str(model_dir.resolve()), **common)
    model = model_cls.from_pretrained(
        str(model_dir.resolve()),
        use_safetensors=False,
        weights_only=True,
        **common,
    )
    return processor, model


class ClapInstrumentDetector:
    model_id = "laion/larger_clap_music"
    model_revision = "a0b4534a14f58e20944452dff00a22a06ce629d1"

    def __init__(self, *, model_dir: Path, receipt_path: Path) -> None:
        self.model_dir = model_dir.resolve()
        self.receipt_path = receipt_path.resolve()
        self._torch = None
        self._processor = None
        self._model = None
        self._text_embeddings = None
        self._prompt_targets: tuple[str, ...] = ()

    def load(self) -> None:
        verify_detector_artifacts(self.model_dir, self.receipt_path)
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required for instrument analysis.")
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        processor, model = load_local_clap(self.model_dir)
        model.eval()
        model.to("cuda")
        prompts: list[str] = []
        targets: list[str] = []
        for target, aliases in PROMPT_ALIASES.items():
            prompts.extend(aliases)
            targets.extend([target] * len(aliases))
        text_inputs = processor(text=prompts, return_tensors="pt", padding=True)
        text_inputs = {key: value.to("cuda") for key, value in text_inputs.items()}
        with torch.inference_mode():
            text_embeddings = model.get_text_features(**text_inputs).pooler_output
            text_embeddings = torch.nn.functional.normalize(text_embeddings, dim=-1)
        self._torch = torch
        self._processor = processor
        self._model = model
        self._text_embeddings = text_embeddings
        self._prompt_targets = tuple(targets)

    def score_windows(self, windows: Sequence[np.ndarray]) -> DetectorScoreResult:
        if self._model is None:
            self.load()
        torch = self._torch
        model = self._model
        processor = self._processor
        text_embeddings = self._text_embeddings
        assert torch is not None and model is not None and processor is not None
        scores_by_window: list[dict[str, float]] = []
        with torch.inference_mode():
            for samples in windows:
                audio_inputs = processor(
                    audio=np.asarray(samples, dtype=np.float32),
                    sampling_rate=48_000,
                    return_tensors="pt",
                )
                audio_inputs = {key: value.to("cuda") for key, value in audio_inputs.items()}
                audio_embeddings = model.get_audio_features(**audio_inputs).pooler_output
                audio_embeddings = torch.nn.functional.normalize(audio_embeddings, dim=-1)
                similarities = (audio_embeddings @ text_embeddings.T)[0].detach().cpu().tolist()
                target_scores = {
                    target: max(
                        score
                        for score, prompt_target in zip(
                            similarities, self._prompt_targets, strict=True
                        )
                        if prompt_target == target
                    )
                    for target in PROMPT_ALIASES
                }
                scores_by_window.append(target_scores)
                del audio_inputs, audio_embeddings
        torch.cuda.synchronize()
        return DetectorScoreResult(
            window_scores=tuple(scores_by_window),
            effective_device="cuda",
            peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved(),
        )

    def close(self) -> None:
        torch = self._torch
        self._text_embeddings = None
        self._model = None
        self._processor = None
        self._torch = None
        gc.collect()
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
