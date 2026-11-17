## ADDED Requirements

### Requirement: RR-SR-005 — Index-vs-eval-set isolation enforced at startup

At startup, the retriever SHALL verify that `resources.retrieval.index` is NOT listed as a
source for any eval set with `isolation: strict`. If it is, the retriever SHALL refuse to start.

**Rationale.** Defense in depth alongside OPA (merge-time) and eval harness (CI-time)
enforcement. The index is a live mutable store; drift happens outside the change proposal
pathway (manual seeding, data ingest). See `docs/postmortems/2026-06-eval-leakage.md`.

#### Scenario: Startup overlap detection
- **Given** `rubric-exemplars-prod` is listed as a source for `rubric_alignment_v3`
- **And** `rubric_alignment_v3.isolation: strict`
- **Then** the retriever SHALL fail to start and emit `eval_isolation_violation` at `CRITICAL`.

#### Scenario: Startup probe gracefully handles bundle fetch failure
- **Given** OPA data bundle is temporarily unreachable
- **Then** the retriever SHALL fail closed (refuse to start), NOT fail open.
