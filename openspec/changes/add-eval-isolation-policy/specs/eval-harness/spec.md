## ADDED Requirements

### Requirement: EH-SR-002 — Isolation enforced at run time

Before invoking a case, the harness SHALL verify that none of the case's `source_documents`
appears in any live retrieval index listed in the capability's `resources.retrieval.index` when
the capability's `eval.isolation == strict`.

**Rationale.** OPA enforces at merge time, but an index can be mutated out-of-band (data
pipeline, manual ops). Runtime enforcement catches this. See
`docs/postmortems/2026-06-eval-leakage.md`.

#### Scenario: Eval case document found in production index
- **Given** case `case_042` has `source_documents: [exemplar_017]`
- **And** `exemplar_017` is present in `rubric-exemplars-prod`
- **Then** the harness SHALL abort the run and emit `eval_leakage_detected` at `CRITICAL`
- **And** SHALL open a P1 incident via the on-call rotation API.
