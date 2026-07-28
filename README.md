# T-STEP-v0

T-STEP-v0 is an experimental, executable typed object-state transition
ledger core for temporal video reasoning.

The current repository snapshot contains:

- typed `StateInterval`, `TransitionBoundary`, `EventOperator`, and
  `StateRecord` contracts;
- provenance, persistent-identity, answer-blindness, and metric-applicability
  validation;
- strict ledger update and query execution with explicit `UNKNOWN` outcomes;
- Phase 0 candidate selection, decode probing, dense temporal review, and
  targeted-boundary tooling;
- unit and semantic-contract tests.

## Current Phase 0 verdict

The first answer-blind TOC-Bench real-video gate reached **7 accepted samples
out of 10**, below the preregistered threshold of 8/10. GPU training,
performance baselines, and corruption experiments therefore remain blocked
until a focused implementation review resolves:

1. event-presupposition failures;
2. overlapping visibility operators;
3. missing pre-gap/post-gap identity anchors;
4. endpoint-aware boundary sampling.

See
[`idea-stage/T_STEP_PHASE0_REAL_VIDEO_GATE_REPORT_20260728.md`](idea-stage/T_STEP_PHASE0_REAL_VIDEO_GATE_REPORT_20260728.md)
for the evidence summary and
[`idea-stage/GPT_PRO_TSTEP_PHASE0_REAL_VIDEO_ROUND1_REVIEW_PROMPT_20260728.md`](idea-stage/GPT_PRO_TSTEP_PHASE0_REAL_VIDEO_ROUND1_REVIEW_PROMPT_20260728.md)
for the focused review prompt.

## Test

```bash
python -m pip install -r requirements-dev.txt
python -B -m pytest
```

The validated local snapshot passes 29 tests.

## Data boundary

This repository does **not** redistribute TOC-Bench videos, extracted frames,
source answer files, or evaluator-only gold. Those artifacts remain subject to
their original dataset terms. Public Phase 0 artifacts contain only schemas,
code, aggregate decisions, and answer-blind feasibility evidence.

## Status

Research prototype. No open-source license has been selected yet.
