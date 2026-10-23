from __future__ import annotations

import html
import re
from pathlib import Path

from .schemas import TranscriptSegment


TIMESTAMP = r"(?:\d{2,}:)?\d{2}:\d{2}[.,]\d{3}"
TIMING = re.compile(rf"^(?P<start>{TIMESTAMP})\s+-->\s+(?P<end>{TIMESTAMP})(?:\s+.*)?$")
TAG = re.compile(r"<[^>]+>")
VOICE = re.compile(r"<v(?:\.[^ >]+)*\s+([^>]+)>", re.IGNORECASE)


def timestamp_to_seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(f"Invalid VTT timestamp: {value}")


def clean_text(value: str) -> str:
    return " ".join(html.unescape(TAG.sub("", value)).split())


def _speaker_from_lines(lines: list[str]) -> str | None:
    for line in lines:
        match = VOICE.search(line)
        if match:
            return " ".join(match.group(1).split()) or None
    return None


def parse_vtt_text(content: str) -> list[TranscriptSegment]:
    lines = content.replace("\ufeff", "").splitlines()
    first_content = next((line.strip() for line in lines if line.strip()), "")
    if not first_content.startswith("WEBVTT"):
        raise ValueError("Upload a valid WebVTT file beginning with WEBVTT.")

    segments: list[TranscriptSegment] = []
    previous_start = -1.0
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if "-->" in line and not TIMING.match(line):
            raise ValueError("The VTT contains an invalid cue timestamp.")
        match = TIMING.match(line)
        if not match:
            index += 1
            continue

        start = timestamp_to_seconds(match.group("start"))
        end = timestamp_to_seconds(match.group("end"))
        if end <= start:
            raise ValueError("The VTT contains a cue whose end time is not after its start time.")
        if start < previous_start:
            raise ValueError("The VTT cue timestamps must be in chronological order.")

        text_lines: list[str] = []
        index += 1
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        text = clean_text(" ".join(text_lines))
        if text:
            segments.append(TranscriptSegment(start_sec=start, end_sec=end, text=text, speaker=_speaker_from_lines(text_lines)))
            previous_start = start
        index += 1

    if not segments:
        raise ValueError("No timed transcript cues were found. Upload a valid WebVTT file.")
    return segments


def parse_vtt_file(path: Path) -> list[TranscriptSegment]:
    return parse_vtt_text(path.read_text(encoding="utf-8-sig", errors="replace"))
