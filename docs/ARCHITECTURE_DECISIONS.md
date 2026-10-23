# Architecture decisions

| Decision | Choice | Reason |
|---|---|---|
| Primary input | WebVTT only | Reliable timestamps with the least challenge-time risk. |
| Transcript context | One complete VTT request | A full class fits the selected local-model context and preserves opening-to-closing context. |
| Evidence extraction | Local Ollama, with approved Groq fallback | Keeps local processing as the default while allowing explicit, gated fallback. |
| Grounding | Quote plus overlapping VTT timestamp | Prevents unsupported model observations from affecting results. |
| Scoring | Fixed event-kind rubric | The LLM provides evidence, while application code determines all scores and labels. |
| Video/Docling | Deferred | Not required for supplied VTTs; retained as a future adapter. |
| Groq | Explicitly gated fallback only | Requires `ALLOW_EXTERNAL_PROCESSING=true` and `GROQ_API_KEY`; auto mode remains local-first. |
| RAG, vectors, Jev | Not used | Outside the time-boxed Phase 1 prototype. |

`OLLAMA_MODEL` must name a locally available model. If it fails, automatic fallback is possible only when Humaniti has approved external processing and the explicit gate/key are configured. No heuristic fallback exists.
