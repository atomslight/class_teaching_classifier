from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from .extractors import ExtractionError, GroqTranscriptExtractor, OllamaTranscriptExtractor, TranscriptExtractor
from .schemas import AssessmentResult, EvidenceEvent, EvidenceProvider, TranscriptSegment
from .scoring import DeterministicRubricScorer
from .validation import deduplicate_events, validate_events
from .vtt import parse_vtt_file


ProviderMode = Literal["auto", "ollama", "groq"]


@dataclass(frozen=True)
class ExtractionOutcome:
    events: list[EvidenceEvent]
    provider: EvidenceProvider
    provider_note: str | None = None


def extract_with_provider(
    segments: list[TranscriptSegment],
    *,
    provider_mode: str | None = None,
    allow_external_processing: bool | None = None,
    groq_api_key: str | None = None,
    ollama_extractor: TranscriptExtractor | None = None,
    groq_extractor_factory: Callable[[], TranscriptExtractor] | None = None,
) -> ExtractionOutcome:
    mode = _provider_mode(provider_mode or os.getenv("EXTRACTION_PROVIDER", "auto"))
    external_allowed = _external_processing_enabled(allow_external_processing)
    api_key = groq_api_key if groq_api_key is not None else os.getenv("GROQ_API_KEY")

    if mode == "ollama":
        return ExtractionOutcome((ollama_extractor or OllamaTranscriptExtractor()).extract(segments), "Local Ollama")

    if mode == "groq":
        _require_groq_permission(external_allowed, api_key)
        return ExtractionOutcome(_groq_extractor(groq_extractor_factory, api_key).extract(segments), "Groq API")

    try:
        events = (ollama_extractor or OllamaTranscriptExtractor()).extract(segments)
    except Exception as ollama_error:
        if not external_allowed:
            raise ExtractionError(
                "Local Ollama extraction failed. External processing is disabled, so the transcript was not sent to Groq. "
                "Verify Ollama and OLLAMA_MODEL, or explicitly enable approved external processing."
            ) from ollama_error
        if not api_key:
            raise ExtractionError(
                "Local Ollama extraction failed and Groq fallback is not configured. The transcript was not sent externally. "
                "Set GROQ_API_KEY only after external processing is approved."
            ) from ollama_error
        try:
            events = _groq_extractor(groq_extractor_factory, api_key).extract(segments)
        except Exception as groq_error:
            detail = (
                str(groq_error)
                if isinstance(groq_error, ExtractionError)
                else "Groq did not return a usable extraction. Verify the approved API configuration and try again."
            )
            raise ExtractionError(
                "Local Ollama extraction failed. An approved Groq API fallback was attempted, but it did not succeed. " + detail,
                provider="Groq API",
                external_request_attempted=True,
            ) from groq_error
        return ExtractionOutcome(events, "Groq API", "Local Ollama unavailable; evidence extracted with approved Groq fallback.")
    return ExtractionOutcome(events, "Local Ollama")


def assess_segments(
    source_name: str,
    segments: list[TranscriptSegment],
    extractor: TranscriptExtractor | None = None,
    *,
    provider_mode: str | None = None,
    allow_external_processing: bool | None = None,
    groq_api_key: str | None = None,
    groq_extractor_factory: Callable[[], TranscriptExtractor] | None = None,
) -> AssessmentResult:
    if not segments:
        raise ValueError("The transcript did not contain any usable timestamped speech.")
    outcome = extract_with_provider(
        segments,
        provider_mode=provider_mode,
        allow_external_processing=allow_external_processing,
        groq_api_key=groq_api_key,
        ollama_extractor=extractor,
        groq_extractor_factory=groq_extractor_factory,
    )
    events = deduplicate_events(validate_events(outcome.events, segments))
    duration = max(segment.end_sec for segment in segments)
    return DeterministicRubricScorer().score(
        source_name,
        duration,
        events,
        provider=outcome.provider,
        provider_note=outcome.provider_note,
    )


def assess_file(path: Path, extractor: TranscriptExtractor | None = None) -> AssessmentResult:
    if path.suffix.lower() != ".vtt":
        raise ValueError("Phase 1 accepts a WebVTT (.vtt) transcript. Video input is planned for Phase 2.")
    return assess_segments(path.name, parse_vtt_file(path), extractor)


def _provider_mode(value: str) -> ProviderMode:
    normalised = value.strip().casefold()
    if normalised not in {"auto", "ollama", "groq"}:
        raise ExtractionError("EXTRACTION_PROVIDER must be auto, ollama, or groq.")
    return normalised  # type: ignore[return-value]


def _external_processing_enabled(value: bool | None) -> bool:
    if value is not None:
        return value
    return os.getenv("ALLOW_EXTERNAL_PROCESSING", "false").strip().casefold() == "true"


def _require_groq_permission(external_allowed: bool, api_key: str | None) -> None:
    if not external_allowed:
        raise ExtractionError("Groq extraction requires ALLOW_EXTERNAL_PROCESSING=true. The transcript was not sent externally.")
    if not api_key:
        raise ExtractionError("Groq extraction requires GROQ_API_KEY. The transcript was not sent externally.")


def _groq_extractor(factory: Callable[[], TranscriptExtractor] | None, api_key: str | None) -> TranscriptExtractor:
    return factory() if factory else GroqTranscriptExtractor(api_key=api_key)
