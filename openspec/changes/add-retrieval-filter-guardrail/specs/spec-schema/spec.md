## ADDED Requirements

### Requirement: SS-SR-006 — RAG capabilities require `retrieval_filter:`

Any capability whose `resources.retrieval.index` is set SHALL also declare
`resources.retrieval.retrieval_filter` (object, not null).

**Rationale.** Retrieval filter was once implicit. See
`docs/postmortems/2026-04-retrieval-filter-leak.md`. The schema no longer permits implicit.

#### Scenario: RAG without retrieval filter
- **Given** a capability spec with `resources.retrieval.index` but no `retrieval_filter`
- **Then** OPA SHALL reject with `retrieval_filter.required`.

#### Scenario: Non-RAG capability
- **Given** a capability spec with `resources.retrieval: null`
- **Then** this requirement SHALL NOT fire; OPA allows the spec regardless of filter presence.

#### Scenario: Grace window
- **Given** `opa.config.retrieval_filter_grace_until` is in the future
- **And** a RAG spec omits `retrieval_filter`
- **Then** OPA SHALL emit `warn` (not `deny`) and record the capability name for backfill
  tracking.
