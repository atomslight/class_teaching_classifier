from __future__ import annotations

from dataclasses import dataclass

from .schemas import TranscriptSegment


@dataclass(frozen=True)
class TranscriptChunk:
    start_sec: float
    end_sec: float
    segments: list[TranscriptSegment]

    @property
    def text(self) -> str:
        return " ".join(segment.text for segment in self.segments)


def make_chunks(segments: list[TranscriptSegment], window_sec: int = 300, overlap_sec: int = 30) -> list[TranscriptChunk]:
    if not segments:
        return []
    duration = max(segment.end_sec for segment in segments)
    chunks: list[TranscriptChunk] = []
    start = 0.0
    while start <= duration:
        end = start + window_sec
        selected = [segment for segment in segments if segment.end_sec >= start and segment.start_sec <= end]
        if selected:
            chunks.append(TranscriptChunk(start, end, selected))
        if end >= duration:
            break
        start += window_sec - overlap_sec
    return chunks
