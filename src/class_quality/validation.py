from __future__ import annotations

import re

from .schemas import DimensionName, EvidenceEvent, TranscriptSegment


KIND_DIMENSIONS: dict[str, DimensionName] = {
    "rapport_exchange": "rapport",
    "learner_prompt": "interaction",
    "comprehension_check": "interaction",
    "inclusive_turn": "interaction",
    "feedback_or_correction": "pedagogy",
    "guided_practice": "pedagogy",
    "recap_or_structure": "lesson_flow",
    "homework_or_next_step": "follow_through",
    "closing": "follow_through",
}


def normalise(value: str) -> str:
    return re.sub(r"\W+", "", value.casefold())


def validate_events(events: list[EvidenceEvent], segments: list[TranscriptSegment]) -> list[EvidenceEvent]:
    valid: list[EvidenceEvent] = []
    for event in events:
        if KIND_DIMENSIONS[event.kind] != event.dimension:
            continue
        quote = normalise(event.evidence_quote)
        if len(quote) < 3:
            continue
        overlapping_segments = [segment for segment in segments if event.end_sec >= segment.start_sec and event.start_sec <= segment.end_sec]
        if overlapping_segments and any(quote in normalise(segment.text) for segment in overlapping_segments):
            valid.append(event)
    return valid


def deduplicate_events(events: list[EvidenceEvent]) -> list[EvidenceEvent]:
    result: list[EvidenceEvent] = []
    seen: set[tuple[str, str, str]] = set()
    for event in sorted(events, key=lambda item: (item.start_sec, item.end_sec, item.kind)):
        key = (event.dimension, event.kind, normalise(event.evidence_quote))
        if key not in seen:
            seen.add(key)
            result.append(event)
    return result
