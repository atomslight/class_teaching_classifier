from class_quality.pipeline import assess_segments
from class_quality.schemas import EvidenceEvent


class FakeExtractor:
    def __init__(self):
        self.calls = []

    def extract(self, segments):
        self.calls.append(segments)
        return [
            EvidenceEvent(
                dimension="rapport",
                kind="rapport_exchange",
                start_sec=0,
                end_sec=3,
                evidence_quote="Hello everyone, how are you today?",
                observation="The transcript shows a welcome exchange.",
            ),
            EvidenceEvent(
                dimension="interaction",
                kind="learner_prompt",
                start_sec=0,
                end_sec=3,
                evidence_quote="Invented text",
                observation="Unsupported event.",
            ),
        ]


def test_pipeline_passes_complete_transcript_to_one_extractor_call(strong_segments):
    extractor = FakeExtractor()
    result = assess_segments("strong.vtt", strong_segments, extractor)
    assert extractor.calls == [strong_segments]
    assert len(result.evidence) == 1
    assert result.evidence[0].kind == "rapport_exchange"
    assert result.provider == "Local Ollama"
