from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


DimensionName = Literal["rapport", "interaction", "pedagogy", "lesson_flow", "follow_through"]
EvidenceKind = Literal[
    "rapport_exchange",
    "learner_prompt",
    "comprehension_check",
    "inclusive_turn",
    "feedback_or_correction",
    "guided_practice",
    "recap_or_structure",
    "homework_or_next_step",
    "closing",
]
QualityLabel = Literal["Poor", "Average", "Good", "Excellent"]
EvidenceProvider = Literal["Local Ollama", "Groq API"]


class TranscriptSegment(BaseModel):
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)
    text: str = Field(min_length=1)
    speaker: str | None = None

    @model_validator(mode="after")
    def end_follows_start(self) -> "TranscriptSegment":
        if self.end_sec <= self.start_sec:
            raise ValueError("end_sec must be after start_sec")
        return self


class EvidenceEvent(BaseModel):
    dimension: DimensionName
    kind: EvidenceKind
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)
    evidence_quote: str = Field(min_length=3, max_length=500)
    observation: str = Field(min_length=3, max_length=500)

    @field_validator("evidence_quote", "observation")
    @classmethod
    def normalise_whitespace(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def ordered_time(self) -> "EvidenceEvent":
        if self.end_sec <= self.start_sec:
            raise ValueError("Evidence event end_sec must be after start_sec")
        return self


class LLMExtraction(BaseModel):
    """The only structured response accepted from the local extraction model."""

    events: list[EvidenceEvent] = Field(default_factory=list, max_length=15)


class EvidenceBundle(BaseModel):
    """Compatibility boundary for callers that need a named source and its events."""

    source_name: str
    source_duration_sec: float = Field(gt=0)
    events: list[EvidenceEvent] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)


class DimensionScore(BaseModel):
    name: DimensionName
    display_name: str
    weight: float = Field(gt=0, le=1)
    score: float = Field(ge=0, le=100)
    rationale: str
    event_count: int = Field(ge=0)


class AssessmentResult(BaseModel):
    label: QualityLabel
    overall_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    dimensions: list[DimensionScore]
    evidence: list[EvidenceEvent]
    coverage_note: str
    caveats: list[str]
    provider: EvidenceProvider = "Local Ollama"
    provider_note: str | None = None
