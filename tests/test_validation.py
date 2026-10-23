from class_quality.schemas import EvidenceEvent
from class_quality.validation import deduplicate_events, validate_events
from class_quality.vtt import parse_vtt_text


def _event(**changes):
    event = EvidenceEvent(
        dimension="rapport",
        kind="rapport_exchange",
        start_sec=0,
        end_sec=2,
        evidence_quote="Hello class",
        observation="The transcript shows a welcome exchange.",
    )
    return event.model_copy(update=changes)


def test_unsupported_quote_or_timestamp_is_removed():
    segments = parse_vtt_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello class\n")
    invented = _event(evidence_quote="Invented words")
    wrong_time = _event(start_sec=20, end_sec=22)
    assert validate_events([invented, wrong_time], segments) == []


def test_wrong_kind_dimension_pair_is_removed():
    segments = parse_vtt_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello class\n")
    invalid_pair = _event(kind="closing")
    assert validate_events([invalid_pair], segments) == []


def test_duplicate_dimension_kind_and_quote_is_merged():
    event = _event()
    duplicate = _event(start_sec=1, end_sec=3)
    assert len(deduplicate_events([event, duplicate])) == 1
