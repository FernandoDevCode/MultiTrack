from __future__ import annotations

from collections.abc import Mapping, Sequence

from stemlab.domain import CANONICAL_TARGETS, InstrumentEvidence


PROMPT_ALIASES: dict[str, tuple[str, ...]] = {
    "vocals": ("singing vocals", "human singing voice", "lead vocals"),
    "drums": ("drum kit", "acoustic drums", "music with drums"),
    "bass": ("bass guitar", "electric bass", "low bass instrument"),
    "guitar": ("electric guitar", "acoustic guitar", "music with guitar"),
    "piano": ("acoustic piano", "grand piano", "music with piano"),
    "keys": ("keyboard instrument", "electronic keyboard", "music with keyboards"),
    "synth_pad": ("synthesizer pad", "synth pad", "electronic synthesizer"),
    "organ": ("organ instrument", "Hammond organ", "pipe organ"),
    "percussion": ("hand percussion", "auxiliary percussion", "music with percussion"),
    "strings": ("string section", "orchestral strings", "violin cello ensemble"),
    "brass": ("brass section", "trumpet trombone", "orchestral brass"),
    "woodwind": ("woodwind section", "flute clarinet", "orchestral woodwinds"),
    "choir": ("mixed choir", "choral singing", "vocal choir"),
}

TARGET_LABELS = {
    "vocals": "Vocals",
    "drums": "Drums",
    "bass": "Bass",
    "guitar": "Guitar",
    "piano": "Piano",
    "keys": "Keys",
    "synth_pad": "Synth / Pad",
    "organ": "Organ",
    "percussion": "Percussion",
    "strings": "Strings",
    "brass": "Brass",
    "woodwind": "Woodwind",
    "choir": "Choir",
}


def aggregate_instrument_evidence(
    window_scores: Sequence[Mapping[str, float]],
) -> tuple[InstrumentEvidence, ...]:
    if not window_scores:
        raise ValueError("At least one analysis window is required.")
    for scores in window_scores:
        if set(scores) != set(CANONICAL_TARGETS):
            raise ValueError("Window scores must contain the exact canonical taxonomy.")

    ranks_by_window: list[dict[str, int]] = []
    for scores in window_scores:
        ordered = sorted(CANONICAL_TARGETS, key=lambda target: (-scores[target], target))
        ranks_by_window.append({target: index + 1 for index, target in enumerate(ordered)})

    aggregates = {
        target: sum(float(scores[target]) for scores in window_scores) / len(window_scores)
        for target in CANONICAL_TARGETS
    }
    aggregate_order = sorted(CANONICAL_TARGETS, key=lambda target: (-aggregates[target], target))
    aggregate_ranks = {target: index + 1 for index, target in enumerate(aggregate_order)}
    suggested_hits = (len(window_scores) + 1) // 2

    evidence: list[InstrumentEvidence] = []
    for target in CANONICAL_TARGETS:
        scores = tuple(float(item[target]) for item in window_scores)
        ranks = tuple(item[target] for item in ranks_by_window)
        strong_hits = sum(rank <= 3 for rank in ranks)
        if strong_hits >= suggested_hits or aggregate_ranks[target] <= 3:
            state = "suggested"
        elif strong_hits > 0 or aggregate_ranks[target] <= 7:
            state = "possible"
        else:
            state = "not_suggested"
        evidence.append(
            InstrumentEvidence(
                target_id=target,
                aggregate_similarity=aggregates[target],
                peak_similarity=max(scores),
                strong_window_hits=strong_hits,
                best_rank=min(ranks),
                state=state,
                window_scores=scores,
                window_ranks=ranks,
            )
        )
    return tuple(evidence)
