from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SeparationStep:
    mode_id: str


@dataclass(frozen=True)
class PipelinePlan:
    pipeline_id: str
    label: str
    description: str
    steps: tuple[SeparationStep, ...]

    def to_dict(self) -> dict:
        return asdict(self)


CORE_STEMS = PipelinePlan(
    pipeline_id="core-stems",
    label="Core Stems",
    description="BS-RoFormer SW: vocals, drums, bass, guitar, piano e other.",
    steps=(SeparationStep(mode_id="six-stems"),),
)

PIPELINES = (CORE_STEMS,)
_BY_ID = {pipeline.pipeline_id: pipeline for pipeline in PIPELINES}


def get_pipeline(pipeline_id: str) -> PipelinePlan:
    try:
        return _BY_ID[pipeline_id]
    except KeyError as exc:
        raise ValueError(f"Unknown pipeline: {pipeline_id}") from exc
