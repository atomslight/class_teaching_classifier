from __future__ import annotations

import copy
import os
from typing import Protocol

from .schemas import EvidenceEvent, LLMExtraction, TranscriptSegment


SUPPORTED_GROQ_MODELS = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}


class ExtractionError(RuntimeError):
    """A user-safe extraction failure that never includes source transcript content."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        external_request_attempted: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.external_request_attempted = external_request_attempted


def _format_timestamp(seconds: float) -> str:
    milliseconds = round((seconds % 1) * 1000)
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02}.{milliseconds:03}"


def format_transcript(segments: list[TranscriptSegment]) -> str:
    lines: list[str] = []
    for segment in segments:
        speaker = f" ({segment.speaker})" if segment.speaker else ""
        lines.append(f"[{_format_timestamp(segment.start_sec)}–{_format_timestamp(segment.end_sec)}]{speaker} {segment.text}")
    return "\n".join(lines)


def build_extraction_prompt(segments: list[TranscriptSegment]) -> str:
    return """You extract grounded evidence from one online-class transcript. Return JSON only, matching the supplied schema.

Return evidence events, never a quality label, score, strength, ranking, or conclusion about the teacher/class. Each observation must be a concise factual description of what the transcript shows, not an evaluative claim. Copy a short direct quote exactly from the transcript and provide the timestamp range covering it.

Allowed dimensions: rapport, interaction, pedagogy, lesson_flow, follow_through.
Allowed kinds: rapport_exchange, learner_prompt, comprehension_check, inclusive_turn, feedback_or_correction, guided_practice, recap_or_structure, homework_or_next_step, closing.

Use at most three events per dimension and fifteen events total. Do not treat an isolated greeting, praise phrase, homework mention, or question as strong evidence. Use rapport_exchange only for a meaningful welcome/check-in exchange. Use learner_prompt only when the local transcript context shows a prompt plus a learner response or follow-up. Use feedback_or_correction only when feedback or correction follows learner interaction. Do not infer camera use, face visibility, background, lighting, actual audio quality, energy/tone, actual participation equity, learner understanding, or subject correctness.

Transcript follows:\n""" + format_transcript(segments)


def strict_extraction_schema() -> dict[str, object]:
    """Adapt Pydantic's schema to Groq strict JSON-schema requirements."""

    schema = copy.deepcopy(LLMExtraction.model_json_schema())

    def make_strict(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                node["additionalProperties"] = False
                node["required"] = list(properties)
            for value in node.values():
                make_strict(value)
        elif isinstance(node, list):
            for value in node:
                make_strict(value)

    make_strict(schema)
    return schema


class TranscriptExtractor(Protocol):
    def extract(self, segments: list[TranscriptSegment]) -> list[EvidenceEvent]: ...


class OllamaTranscriptExtractor:
    """One local structured-extraction call over the complete VTT timeline."""

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
        client: object | None = None,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL")
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.num_ctx = num_ctx or _positive_env_int("OLLAMA_NUM_CTX", 32768)
        self.num_predict = num_predict or _positive_env_int("OLLAMA_NUM_PREDICT", 2000)
        self.client = client

    def extract(self, segments: list[TranscriptSegment]) -> list[EvidenceEvent]:
        if not self.model:
            raise ExtractionError("Set OLLAMA_MODEL to a locally available Ollama model before assessing a transcript.")
        if not segments:
            return []
        client = self.client
        if client is None:
            try:
                from ollama import Client
            except ImportError as error:
                raise ExtractionError("Install the ollama package to use local transcript extraction.") from error
            client = Client(host=self.host)
        try:
            response = client.chat(
                model=self.model,
                messages=[{"role": "user", "content": build_extraction_prompt(segments)}],
                format=LLMExtraction.model_json_schema(),
                options={"temperature": 0, "num_ctx": self.num_ctx, "num_predict": self.num_predict},
            )
            message = response.message if hasattr(response, "message") else response["message"]
            content = message.content if hasattr(message, "content") else message["content"]
            return LLMExtraction.model_validate_json(content).events
        except ExtractionError:
            raise
        except Exception as error:
            raise ExtractionError(
                "Local Ollama extraction failed. Verify Ollama is running and the configured model is available.",
                provider="Local Ollama",
            ) from error


class GroqTranscriptExtractor:
    """Approved external fallback using Groq strict JSON Schema output."""

    def __init__(self, api_key: str | None = None, model: str | None = None, client: object | None = None) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        if self.model not in SUPPORTED_GROQ_MODELS:
            raise ExtractionError("GROQ_MODEL must be openai/gpt-oss-20b or openai/gpt-oss-120b.")
        self.client = client

    def extract(self, segments: list[TranscriptSegment]) -> list[EvidenceEvent]:
        if not self.api_key:
            raise ExtractionError("Set GROQ_API_KEY before using Groq extraction.")
        if not segments:
            return []
        client = self.client
        if client is None:
            try:
                from groq import Groq
            except ImportError as error:
                raise ExtractionError("Install the groq package to use approved Groq extraction.") from error
            client = Groq(api_key=self.api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": build_extraction_prompt(segments)}],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "humaniti_evidence_extraction",
                        "strict": True,
                        "schema": strict_extraction_schema(),
                    },
                },
            )
            content = response.choices[0].message.content
            return LLMExtraction.model_validate_json(content).events
        except ExtractionError:
            raise
        except Exception as error:
            raise ExtractionError(
                _safe_groq_failure_message(error),
                provider="Groq API",
                external_request_attempted=True,
            ) from error


def _safe_groq_failure_message(error: Exception) -> str:
    """Classify provider errors without rendering exception text or request data."""

    status_code = getattr(error, "status_code", None)
    error_type = type(error).__name__
    if status_code in {401, 403}:
        return "Groq authentication or permission failed. Verify GROQ_API_KEY and its access without exposing it."
    if status_code == 404:
        return "Groq could not find the configured model. Set GROQ_MODEL to openai/gpt-oss-20b or openai/gpt-oss-120b."
    if status_code == 400:
        return "Groq rejected the extraction request. Verify the selected model supports strict JSON Schema output."
    if status_code == 413:
        return "Groq rejected the request as too large. Reduce the transcript only with an approved future design change."
    if status_code == 429:
        return "Groq is rate-limited or the account quota is unavailable. Wait and check the Groq account limits."
    if isinstance(status_code, int) and status_code >= 500:
        return "Groq is temporarily unavailable. Try again later."
    if error_type in {"APITimeoutError", "TimeoutError"}:
        return "The Groq request timed out. Check the network or try again later."
    if error_type in {"APIConnectionError", "ConnectionError"}:
        return "The Groq API could not be reached. Check the network connection and try again."
    return "Groq extraction failed before a usable structured response was received. Verify the approved API configuration and try again."


def _positive_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ExtractionError(f"{name} must be a positive integer.") from error
    if parsed <= 0:
        raise ExtractionError(f"{name} must be a positive integer.")
    return parsed
