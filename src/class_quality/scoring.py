from __future__ import annotations

from .schemas import AssessmentResult, DimensionName, DimensionScore, EvidenceEvent, EvidenceProvider, QualityLabel


DIMENSIONS: dict[DimensionName, tuple[str, float]] = {
    "rapport": ("Rapport and onboarding", 0.20),
    "interaction": ("Interaction and inclusion", 0.30),
    "pedagogy": ("Pedagogy and feedback", 0.20),
    "lesson_flow": ("Lesson flow", 0.15),
    "follow_through": ("Follow-through and closing", 0.15),
}
BASE_SCORES = {0: 0.0, 1: 45.0, 2: 70.0, 3: 90.0}


def _label(score: float) -> QualityLabel:
    if score >= 75:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 45:
        return "Average"
    return "Poor"


def _has_contextual_maximum(name: DimensionName, grouped: dict[DimensionName, list[EvidenceEvent]]) -> bool:
    kinds = {event.kind for event in grouped[name]}
    if name == "rapport":
        return "rapport_exchange" in kinds
    if name == "interaction":
        return "learner_prompt" in kinds
    if name == "pedagogy":
        return {"feedback_or_correction", "guided_practice"}.issubset(kinds)
    if name == "lesson_flow":
        return "recap_or_structure" in kinds and any(
            closing.kind == "closing" and closing.start_sec > recap.start_sec
            for recap in grouped[name]
            for closing in grouped["follow_through"]
        )
    return {"homework_or_next_step", "closing"}.issubset(kinds)


def _score_dimension(name: DimensionName, grouped: dict[DimensionName, list[EvidenceEvent]]) -> DimensionScore:
    display_name, weight = DIMENSIONS[name]
    events = grouped[name]
    kind_count = min(3, len({event.kind for event in events}))
    score = 100.0 if _has_contextual_maximum(name, grouped) else BASE_SCORES[kind_count]
    if not events:
        rationale = "No validated transcript evidence was found for this dimension."
    else:
        kinds = ", ".join(sorted({event.kind.replace("_", " ") for event in events}))
        rationale = f"Validated evidence types: {kinds}."
    return DimensionScore(name=name, display_name=display_name, weight=weight, score=score, rationale=rationale, event_count=len(events))


class DeterministicRubricScorer:
    """Fixed rubric over validated event kinds; the LLM never supplies a score."""

    def score(
        self,
        source_name: str,
        duration_sec: float,
        events: list[EvidenceEvent],
        *,
        provider: EvidenceProvider = "Local Ollama",
        provider_note: str | None = None,
    ) -> AssessmentResult:
        grouped: dict[DimensionName, list[EvidenceEvent]] = {
            name: [event for event in events if event.dimension == name] for name in DIMENSIONS
        }
        dimensions = [_score_dimension(name, grouped) for name in DIMENSIONS]
        overall = sum(item.score * item.weight for item in dimensions)
        supported_dimensions = sum(bool(grouped[name]) for name in DIMENSIONS)
        confidence = min(0.90, 0.25 + (0.08 * supported_dimensions) + (0.025 * min(len(events), 10)))
        caveats = [
            "This is a transcript-led prototype result, not a trained-model prediction.",
            "It cannot verify camera use, face visibility, background, lighting, actual audio quality, teacher energy, equitable participation, or subject correctness.",
        ]
        if duration_sec < 600:
            caveats.append("The transcript covers under ten minutes; evidence confidence is limited.")
        return AssessmentResult(
            label=_label(overall),
            overall_score=round(overall, 1),
            confidence=round(confidence, 2),
            dimensions=dimensions,
            evidence=events,
            coverage_note=f"Analysed {duration_sec / 60:.1f} minutes of timestamped transcript from {source_name}.",
            caveats=caveats,
            provider=provider,
            provider_note=provider_note,
        )
