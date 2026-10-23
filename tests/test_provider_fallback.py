import json
from types import SimpleNamespace

import pytest

from class_quality.extractors import ExtractionError, GroqTranscriptExtractor
from class_quality.pipeline import assess_segments, extract_with_provider
from class_quality.schemas import EvidenceEvent
from class_quality.vtt import parse_vtt_text


def _segments():
    return parse_vtt_text("WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nHello class\n")


def _event():
    return EvidenceEvent(
        dimension="rapport",
        kind="rapport_exchange",
        start_sec=0,
        end_sec=3,
        evidence_quote="Hello class",
        observation="The transcript shows a welcome exchange.",
    )


class FakeExtractor:
    def __init__(self, events=None, error=None):
        self.events = events or [_event()]
        self.error = error
        self.calls = []

    def extract(self, segments):
        self.calls.append(segments)
        if self.error:
            raise self.error
        return self.events


def test_auto_uses_ollama_without_calling_groq():
    ollama = FakeExtractor()
    factory_calls = []
    outcome = extract_with_provider(
        _segments(),
        provider_mode="auto",
        allow_external_processing=True,
        groq_api_key="test-key",
        ollama_extractor=ollama,
        groq_extractor_factory=lambda: factory_calls.append(True),
    )
    assert outcome.provider == "Local Ollama"
    assert factory_calls == []
    assert len(ollama.calls) == 1


def test_auto_falls_back_to_groq_only_when_approved():
    ollama = FakeExtractor(error=RuntimeError("offline"))
    groq = FakeExtractor()
    outcome = extract_with_provider(
        _segments(),
        provider_mode="auto",
        allow_external_processing=True,
        groq_api_key="test-key",
        ollama_extractor=ollama,
        groq_extractor_factory=lambda: groq,
    )
    assert outcome.provider == "Groq API"
    assert outcome.provider_note == "Local Ollama unavailable; evidence extracted with approved Groq fallback."
    assert len(groq.calls) == 1


def test_assessment_result_identifies_groq_fallback():
    result = assess_segments(
        "synthetic.vtt",
        _segments(),
        FakeExtractor(error=RuntimeError("offline")),
        provider_mode="auto",
        allow_external_processing=True,
        groq_api_key="test-key",
        groq_extractor_factory=FakeExtractor,
    )
    assert result.provider == "Groq API"
    assert result.provider_note == "Local Ollama unavailable; evidence extracted with approved Groq fallback."


def test_auto_failure_does_not_call_groq_when_external_processing_is_disabled():
    factory_calls = []
    with pytest.raises(ExtractionError, match="not sent to Groq"):
        extract_with_provider(
            _segments(),
            provider_mode="auto",
            allow_external_processing=False,
            groq_api_key="test-key",
            ollama_extractor=FakeExtractor(error=RuntimeError("offline")),
            groq_extractor_factory=lambda: factory_calls.append(True),
        )
    assert factory_calls == []


def test_auto_groq_failure_discloses_attempt_without_leaking_provider_error():
    sensitive_error = RuntimeError("private transcript text and API key")
    with pytest.raises(ExtractionError) as raised:
        extract_with_provider(
            _segments(),
            provider_mode="auto",
            allow_external_processing=True,
            groq_api_key="test-key",
            ollama_extractor=FakeExtractor(error=RuntimeError("offline")),
            groq_extractor_factory=lambda: FakeExtractor(error=sensitive_error),
        )
    message = str(raised.value)
    assert "Groq API fallback was attempted" in message
    assert "private transcript text" not in message
    assert "API key" not in message
    assert raised.value.external_request_attempted is True


def test_groq_mode_requires_permission_and_key_without_calling_groq():
    factory_calls = []
    with pytest.raises(ExtractionError, match="ALLOW_EXTERNAL_PROCESSING=true"):
        extract_with_provider(
            _segments(),
            provider_mode="groq",
            allow_external_processing=False,
            groq_api_key="test-key",
            groq_extractor_factory=lambda: factory_calls.append(True),
        )
    with pytest.raises(ExtractionError, match="GROQ_API_KEY"):
        extract_with_provider(
            _segments(),
            provider_mode="groq",
            allow_external_processing=True,
            groq_api_key="",
            groq_extractor_factory=lambda: factory_calls.append(True),
        )
    assert factory_calls == []


class FakeGroqClient:
    def __init__(self):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"events": [_event().model_dump()]})))])


def test_groq_uses_strict_schema_and_full_transcript_once():
    client = FakeGroqClient()
    events = GroqTranscriptExtractor(api_key="test-key", client=client).extract(_segments())
    assert len(events) == 1
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["model"] == "openai/gpt-oss-20b"
    assert call["temperature"] == 0
    assert "Hello class" in call["messages"][0]["content"]
    response_format = call["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["events"]
    assert schema["$defs"]["EvidenceEvent"]["additionalProperties"] is False


def test_groq_rejects_unapproved_models():
    with pytest.raises(ExtractionError, match="GROQ_MODEL"):
        GroqTranscriptExtractor(api_key="test-key", model="qwen/not-permitted")


def test_groq_classifies_authentication_failure_without_provider_text():
    class AuthError(Exception):
        status_code = 401

    class FailingGroqClient:
        chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **_: (_ for _ in ()).throw(AuthError("key=secret"))))

    with pytest.raises(ExtractionError) as raised:
        GroqTranscriptExtractor(api_key="test-key", client=FailingGroqClient()).extract(_segments())
    assert "authentication or permission" in str(raised.value)
    assert "key=secret" not in str(raised.value)
    assert raised.value.external_request_attempted is True
