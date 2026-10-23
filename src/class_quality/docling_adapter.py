from __future__ import annotations

from pathlib import Path

from .schemas import TranscriptSegment


def transcribe_video_with_docling(path: Path) -> list[TranscriptSegment]:
    """Best-effort local Docling adapter for video. Direct VTT remains the preferred path.

    Docling video support and timestamp export change independently of this application. The
    adapter therefore refuses to fabricate cue times when the installed version cannot expose them.
    """
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as error:
        raise RuntimeError("Video upload requires local Docling. Install requirements-phase1.txt first.") from error
    result = DocumentConverter().convert(str(path))
    document = result.document
    segments: list[TranscriptSegment] = []
    for item, _level in document.iterate_items():
        text = getattr(item, "text", None)
        start = getattr(item, "start_time", getattr(item, "start_sec", None))
        end = getattr(item, "end_time", getattr(item, "end_sec", None))
        if text and start is not None and end is not None and float(end) > float(start):
            segments.append(TranscriptSegment(start_sec=float(start), end_sec=float(end), text=str(text)))
    if not segments:
        raise RuntimeError(
            "The installed Docling video pipeline did not expose timestamped transcript cues. "
            "Upload the recording's VTT file, or configure a Docling version with VideoPipeline timestamp export."
        )
    return segments
