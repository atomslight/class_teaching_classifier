import pytest

from class_quality.vtt import parse_vtt_text, timestamp_to_seconds


def test_parses_timed_cues():
    segments = parse_vtt_text("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello <i>class</i>\n")
    assert len(segments) == 1
    assert segments[0].start_sec == 1
    assert segments[0].text == "Hello class"


def test_rejects_no_cues():
    with pytest.raises(ValueError, match="No timed"):
        parse_vtt_text("WEBVTT\n\nNo transcript")


def test_rejects_missing_webvtt_header():
    with pytest.raises(ValueError, match="beginning with WEBVTT"):
        parse_vtt_text("00:00:01.000 --> 00:00:03.000\nHello class\n")


def test_preserves_voice_label():
    segments = parse_vtt_text("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n<v Tutor>Hello class</v>\n")
    assert segments[0].speaker == "Tutor"


def test_timestamp_supports_hours():
    assert timestamp_to_seconds("01:02:03.500") == 3723.5
