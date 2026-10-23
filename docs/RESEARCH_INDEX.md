# Research index and handling rules

## Private archive

`private_research/` is deliberately ignored by Git. It contains work derived from the confidential sample recordings:

- `dataset-analysis.md` — inventory and dataset-level observations.
- `vtt-only-patterns.md` — transcript-visible candidate signal catalogue and limitations.
- `vtt-ground-truth-rough-map.md` — comparison of VTT patterns against the eight supplied ordinary labels.
- `vtt-pattern-data.json` — detailed extracted pattern data; keep local only.
- `phase1-rubric-calibration.md` — private baseline calibration of the deterministic scorer.
- `PRIVATE_DATA_NOTE.md` — handling restrictions.

## Findings incorporated into Phase 1

The strongest transcript-level hypotheses are not simple keywords. They are teaching interaction patterns: rapport/check-in followed by learner response, tutor prompts followed by learner participation and feedback, comprehension checks, inclusive turn allocation, structured recap/transition, and a close with next steps.

The limited dataset shows useful Excellent-versus-Weak directional differences for rapport, comprehension checking, positive feedback, inclusion, and closing. It does **not** establish a monotonic four-class rule. Correction/explanation language is highest in some Good examples, homework appears in Average examples, and technical wording does not indicate class quality. For this reason Phase 1 uses separate dimensions and evidence review rather than a keyword threshold classifier.

## Do not infer from VTT

VTT cannot reliably establish background, camera/face visibility, lighting, audio clarity, vocal energy, actual equitable participation, or subject-matter correctness. It may have noisy speakers, embedded instructional-video narration, late starts, early ends, and garbled Malayalam transcription. The UI and report must state these limits.
