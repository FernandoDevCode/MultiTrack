from __future__ import annotations

from dataclasses import asdict, dataclass

from stemlab.domain import ConfirmedTargets, TargetCapability


@dataclass(frozen=True)
class SeparationStep:
    mode_id: str


@dataclass(frozen=True)
class PipelinePlan:
    pipeline_id: str
    label: str
    description: str
    steps: tuple[SeparationStep, ...]
    confirmed_targets: tuple[str, ...] = ()
    capabilities: tuple[TargetCapability, ...] = ()

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


_CORE_TARGETS = frozenset({"vocals", "drums", "bass", "guitar", "piano"})


def plan_for_targets(confirmed: ConfirmedTargets) -> PipelinePlan:
    capabilities = tuple(
        TargetCapability(
            target_id=target,
            status="core_available" if target in _CORE_TARGETS else "specialist_unavailable",
            pipeline_id="core-stems" if target in _CORE_TARGETS else None,
            stem_role=target if target in _CORE_TARGETS else None,
        )
        for target in confirmed.target_ids
    )
    has_core_target = any(item.status == "core_available" for item in capabilities)
    return PipelinePlan(
        pipeline_id="adaptive-instrumentation",
        label="Plano adaptativo",
        description="Plano confirmado pelo usuário para as capacidades atualmente disponíveis.",
        steps=CORE_STEMS.steps if has_core_target else (),
        confirmed_targets=confirmed.target_ids,
        capabilities=capabilities,
    )
