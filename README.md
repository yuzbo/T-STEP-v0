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

The first answer-blind TOC-Bench real-video gate reached **7/10** and failed.
After a focused review, the repository implemented v0.2 contracts for event
presupposition, operational visibility, persistent identity certificates, and
endpoint-aware sampling. A presealed, all-new, no-replacement R2 then reached
**6/10 overall, 3/5 event/order, and 3/5 identity/visibility**; all three
preregistered gates failed.

GPU training, performance baselines, and corruption experiments therefore
remain blocked. The executable ledger core is retained, while TOC-Bench is now
treated as a diagnostic/negative-example source rather than the sole source of
strict ledger supervision.

See the
[`R2 experiment record`](research-wiki/experiments/toc-r2-contract-resample.md),
[`manual review`](data/phase0/toc_phase0_r2_manual_review.json), and
[`machine-checked gate result`](data/phase0/toc_phase0_r2_gate_result.json).

## Test

```bash
python -m pip install -r requirements-dev.txt
python -B -m pytest
```

The current validated snapshot passes 68 tests.

## Data boundary

This repository does **not** redistribute TOC-Bench videos, extracted frames,
source answer files, or evaluator-only gold. Those artifacts remain subject to
their original dataset terms. Public Phase 0 artifacts contain only schemas,
code, aggregate decisions, and answer-blind feasibility evidence.

Files under `examples/tstep_v0/` are fully synthetic test fixtures. Their
invented answer fields exercise mapping and executor behavior and are not
copied from any benchmark.

## Status

Research prototype. No open-source license has been selected yet.
