# Humaniti AI — Phase 1 class-quality assessor

## Project overview

Humaniti AI is a Phase 1 prototype for transcript-led assessment of an online class. Upload a WebVTT (`.vtt`) transcript and the application produces a **Poor**, **Average**, **Good**, or **Excellent** assessment with inspectable, timestamped evidence.

This is a fixed-rubric prototype, not a trained-model prediction or a complete classroom-observation system.

## What the prototype does

The active workflow is:

```text
VTT upload
  → local VTT parsing into timestamped cues
  → one complete-transcript LLM evidence-extraction call
  → quote/timestamp grounding validation and deduplication
  → deterministic rubric scoring
  → Streamlit result
```

The LLM is limited to extracting concise, factual evidence events. It must not assign labels, scores, confidence, rankings, or generic quality conclusions. Code validates the evidence and calculates the final result.

The app accepts valid WebVTT files with chronological, non-empty timed cues. It normalises cue text, retains available voice labels, and displays each accepted observation with its quote and time range.

## What it does not assess

A VTT transcript cannot establish:

- camera use, face visibility, background, or lighting;
- actual audio quality or teacher energy/tone;
- equitable participation or learner understanding beyond what the transcript directly shows;
- subject correctness;
- video, audio, or recording files directly.

Video and audio analysis are deferred work; Phase 1 accepts `.vtt` files only.

## Architecture and data flow

The Streamlit UI saves the upload in a temporary directory for the duration of the assessment. The local parser turns the VTT into timestamped transcript segments. The selected provider receives the complete formatted transcript in one structured extraction request.

Each returned event must use one of the supported event kinds and the matching scoring dimension. Before it is scored, the app checks that its normalised quote occurs in a VTT cue overlapping its stated time range. It then removes duplicates with the same dimension, kind, and quote. Unsupported, misclassified, ungrounded, or duplicate events do not contribute to the result.

```text
Streamlit upload → parse_vtt_file → provider extraction (once)
                                      ↓
                         validate_events + deduplicate_events
                                      ↓
                         DeterministicRubricScorer → UI
```

## System requirements

- Python `>=3.11,<3.14`; Python 3.12 is recommended for the most straightforward setup.
- [`uv`](https://docs.astral.sh/uv/) for environment and package management.
- [Ollama](https://ollama.com/) for the default local extraction path.
- Internet access only to install packages or pull an Ollama model. It is also required for Groq only when external processing has been explicitly approved.
- A GPU is optional. CPU execution is supported, though long transcripts can be slow.

For a practical local setup with `llama3.1:8b`, approximately 16 GB RAM and roughly 10 GB of free disk space are recommended guidance, not hard guarantees. Actual capacity depends on the operating system, model runtime, and transcript length.

## New-system installation using `uv`

From PowerShell, clone or open this repository and run:

```powershell
winget install --id astral-sh.uv -e
winget install --id Ollama.Ollama -e

ollama pull llama3.1:8b
ollama list

uv venv --python 3.12
uv pip install -r requirements-phase1.txt
uv pip install -e .

Copy-Item .env.example .env
uv run streamlit run app.py
```

The final command starts the local Streamlit application. If PowerShell cannot find `uv` or `ollama` immediately after installation, open a new PowerShell window and retry.

## Ollama setup

The default configuration expects a locally running Ollama server at `http://localhost:11434` and the model `llama3.1:8b`.

After installation, verify that the model is present:

```powershell
ollama list
```

If it is not listed, pull it:

```powershell
ollama pull llama3.1:8b
```

On a typical Windows installation, Ollama runs as a local background service. If the app reports that it cannot reach Ollama, start Ollama and confirm the host and model values in `.env`. The default context and output limits are `OLLAMA_NUM_CTX=32768` and `OLLAMA_NUM_PREDICT=2000`; use positive integers if adjusting them for a machine with sufficient memory.

## Environment configuration

Create the local configuration file from the safe-to-commit template:

```powershell
Copy-Item .env.example .env
```

Keep `.env` private and never commit it. Its supported settings are:

| Setting | Default | Purpose |
| --- | --- | --- |
| `EXTRACTION_PROVIDER` | `auto` | `auto`, `ollama`, or `groq` provider mode. |
| `OLLAMA_MODEL` | `llama3.1:8b` | Locally available Ollama model. |
| `OLLAMA_HOST` | `http://localhost:11434` | Local Ollama endpoint. |
| `OLLAMA_NUM_CTX` | `32768` | Positive context-window setting sent to Ollama. |
| `OLLAMA_NUM_PREDICT` | `2000` | Positive output-token limit sent to Ollama. |
| `ALLOW_EXTERNAL_PROCESSING` | `false` | External-processing approval gate. |
| `GROQ_API_KEY` | empty | Required only for approved Groq use. |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq model; only `openai/gpt-oss-20b` and `openai/gpt-oss-120b` are supported. |

For the standard local-only setup, leave `EXTRACTION_PROVIDER=auto` or set it to `ollama`, and keep `ALLOW_EXTERNAL_PROCESSING=false`.

## Running the Streamlit application

Activate nothing manually when using `uv`; from the repository root, run:

```powershell
uv run streamlit run app.py
```

Open the local URL printed by Streamlit, upload a `.vtt` transcript, and select **Assess class**. The page reports the overall label and score, evidence confidence, provider, validated observations, per-dimension scores, and caveats. The uploaded file is held in a temporary directory during processing and is removed when that assessment completes.

## Provider and privacy behaviour

`auto` is local-first: it uses Ollama and does not call Groq when local extraction succeeds. If local extraction fails, a Groq fallback is possible only when both of the following are true:

1. `ALLOW_EXTERNAL_PROCESSING=true` has been explicitly set after Humaniti approval.
2. `GROQ_API_KEY` is configured.

If either condition is absent, the transcript is not sent to Groq. Set `EXTRACTION_PROVIDER=ollama` to disable fallback completely. Set `EXTRACTION_PROVIDER=groq` only for an explicitly approved external run; this mode also requires the approval flag and API key.

Both providers receive the complete transcript for evidence extraction only. Local Ollama processes it through the configured local endpoint. Groq processing is external and must not be enabled without explicit Humaniti approval. Provider failures are presented without reproducing source-transcript contents or provider exception details.

## How scoring works

The rubric has five weighted dimensions:

| Dimension | Weight |
| --- | ---: |
| Rapport and onboarding | 20% |
| Interaction and inclusion | 30% |
| Pedagogy and feedback | 20% |
| Lesson flow | 15% |
| Follow-through and closing | 15% |

Accepted evidence kinds are fixed:

- `rapport_exchange`
- `learner_prompt`
- `comprehension_check`
- `inclusive_turn`
- `feedback_or_correction`
- `guided_practice`
- `recap_or_structure`
- `homework_or_next_step`
- `closing`

Each kind maps to exactly one dimension. Within a dimension, the number of distinct validated kinds yields a base score of 0, 45, 70, or 90 for 0, 1, 2, or 3-or-more kinds. Contextual combinations can award 100: a rapport exchange; a learner prompt; both feedback/correction and guided practice; recap/structure followed by a closing; or both homework/next step and closing. The weighted dimension scores form the overall score.

Overall labels use these thresholds: **Poor** below 45, **Average** from 45 to below 60, **Good** from 60 to below 75, and **Excellent** at 75 or above.

Evidence confidence is a coverage indicator derived from the number of supported dimensions and accepted events, capped at 90%; it is not a model-provided confidence score. Results for transcripts shorter than ten minutes include an additional caveat.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| “Upload a valid WebVTT…” or no timed cues | Confirm the file begins with `WEBVTT` and contains valid, chronological cue timestamps. |
| Ollama extraction failed | Confirm Ollama is running, `OLLAMA_HOST` is correct, and `ollama list` shows the configured `OLLAMA_MODEL`. |
| Model is missing | Run `ollama pull llama3.1:8b`, or set `OLLAMA_MODEL` to a model already shown by `ollama list`. |
| Long transcript is slow or fails locally | CPU processing may take time. Ensure sufficient RAM and consider only approved operational changes to model/context settings. |
| Groq is not used after a local failure | This is expected unless `ALLOW_EXTERNAL_PROCESSING=true` and `GROQ_API_KEY` are both configured. |
| Groq configuration error | Use one of the two supported Groq models and verify approval, network access, and credentials without printing or sharing the key. |
| Assessment has little or no evidence | The extractor may return no events that pass grounding validation; inspect the transcript quality and timestamps, not private content in logs. |

## Testing

The test suite uses synthetic parser and provider-client scenarios, including VTT parsing, evidence grounding and deduplication, deterministic scoring, full-transcript single-call extraction, and provider fallback safeguards.

Run it from the repository root:

```powershell
uv run pytest
```

## Project layout

```text
app.py                         Streamlit VTT upload and result interface
src/class_quality/
  vtt.py                       WebVTT parsing and cue normalisation
  extractors.py                Ollama/Groq evidence extraction and schemas
  validation.py                Evidence grounding and deduplication
  scoring.py                   Fixed weighted rubric and labels
  pipeline.py                  Parse, extract, validate, and score orchestration
  schemas.py                   Typed transcript, evidence, and result models
tests/                         Synthetic test suite and fixtures
requirements-phase1.txt        Runtime and test dependencies
.env.example                   Safe environment-variable template
```

`chunking.py` and `docling_adapter.py` are not part of the active Phase 1 VTT flow.

## Phase 2 / deferred work

The following are intentionally outside the active Phase 1 implementation:

- direct recording, audio, and video ingestion;
- reliable video-derived observations such as camera use, visibility, lighting, and background;
- audio-quality or delivery analysis;
- production calibration, labels, and evaluation material;
- any broader classroom-quality claims that cannot be grounded in timestamped transcript text.

## Confidentiality and safe-handling rules

Treat all real transcripts and related materials as sensitive.

- Keep `Humaniti AI Dataset/`, `private_research/`, recordings, uploaded VTT files, feedback, labels, calibration material, and `.env` local and private.
- Do not read, copy, quote, summarise, commit, publish, upload, or send those materials to external services unless separately authorised.
- Do not enable `ALLOW_EXTERNAL_PROCESSING=true` unless Humaniti has explicitly approved the external transfer for that run.
- Use the synthetic tests and safe configuration template for development and verification.
