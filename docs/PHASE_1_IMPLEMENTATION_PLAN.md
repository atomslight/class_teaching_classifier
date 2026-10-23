# Phase 1 implementation

Phase 1 deliberately uses the smallest explainable local path:

```text
VTT -> timestamped transcript cues -> one local-first provider JSON extraction
    -> quote/timestamp validation -> fixed rubric -> Streamlit result
```

The model returns no label, score, ranking, or confidence. It returns only up to 15 typed evidence events. The application drops events whose direct quote does not occur in a source cue overlapping the claimed timestamp, de-duplicates events by dimension, kind, and quote, then applies the deterministic rubric.

The user-facing labels are Poor, Average, Good, and Excellent. `Poor` is displayed even where private supplied material historically uses `weak`.

The active demo accepts only VTT. Ollama is the default provider; Groq is permitted only through the explicit external-processing gate. Local video transcription and all audio/visual signals are deferred to Phase 2.

## Calibration

Privately compare the fixed VTT pipeline with the eight ordinary labelled sessions only. Exclude demos and quality-issue sessions, never feed labels/folder names/feedback into inference, and retain the comparison locally as a development check rather than an accuracy claim.
