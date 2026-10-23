# Humaniti AI — Phase 1 class-quality assessor

This local Streamlit prototype assesses a WebVTT class transcript and returns a **Poor**, **Average**, **Good**, or **Excellent** VTT-only result with timestamped supporting quotes.

## Phase 1 flow

```text
VTT upload -> local VTT parser -> one complete provider extraction call
           -> quote/timestamp validation -> fixed rubric -> Streamlit result
```

The extraction model returns evidence only. It does not assign a label, score, or confidence. Deterministic code validates the evidence and applies the rubric.

## What it assesses

- rapport and onboarding;
- interaction and inclusion;
- pedagogy and feedback;
- lesson flow;
- follow-through and closing.

The application cannot verify camera use, face visibility, background, lighting, actual audio quality, teacher energy, equitable participation, learner understanding, or subject correctness from a VTT.

## Run locally

1. Use Python 3.11 or 3.12.
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements-phase1.txt` then `pip install -e .`.
4. Install and start Ollama, pull **llama3.1:8b**, and set it in `.env`.
5. Start the UI: `streamlit run app.py`.

Upload a `.vtt` file. The app processes the complete normalized transcript in one local Ollama request and deletes the temporary upload after the assessment finishes.

Start with `OLLAMA_NUM_CTX=32768` and `OLLAMA_NUM_PREDICT=2000`. Increase the context to `40960` or `49152` only if Ollama reports truncation and local memory permits it.

## Providers and confidentiality

`EXTRACTION_PROVIDER=auto` tries local Ollama first. Set `ollama` to disable fallback completely. `groq` uses only Groq, but requires both `ALLOW_EXTERNAL_PROCESSING=true` and `GROQ_API_KEY`.

The Groq fallback defaults to `openai/gpt-oss-20b`; `openai/gpt-oss-120b` is the only supported stronger option. Both use strict JSON Schema output. Never set `ALLOW_EXTERNAL_PROCESSING=true` unless Humaniti has explicitly approved external processing.

The supplied recordings and research may contain sensitive material. Keep `Humaniti AI Dataset/`, `private_research/`, uploads, transcript output, and `.env` local. Do not commit, publish, upload, or send them to external services. When the external-processing gate is false, the app never sends transcripts to Groq.

## Project map

- `app.py` — VTT-only Streamlit UI.
- `src/class_quality/` — parser, local LLM extraction, grounding validation, and fixed scorer.
- `tests/` — synthetic, non-confidential fixtures and tests.
- `private_research/` — local calibration context; excluded from source control.

Video/audio analysis is intentionally deferred to Phase 2.
