# Phase 1 data contracts

`src/class_quality/schemas.py` is the source of truth.

The local model must return a JSON object with an `events` list of at most 15 entries. Each event contains:

- one of five dimensions: `rapport`, `interaction`, `pedagogy`, `lesson_flow`, or `follow_through`;
- one fixed evidence kind;
- start and end seconds;
- a short direct VTT quote;
- a factual observation of what the transcript shows.

The model may not return scores, labels, strengths, or quality conclusions. `AssessmentResult` is produced only after validation and deterministic scoring, and records whether evidence came from Local Ollama or approved Groq fallback.

An accepted event must have a valid kind/dimension pair, a non-empty normalized quote, an overlapping timed source cue, and that quote within the overlapping cue. Duplicate dimension/kind/quote combinations are retained once.
