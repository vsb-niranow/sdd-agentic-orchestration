## MODIFIED Requirements

### Requirement: EF-SR-003 — Grade-band retrieval filter

**Prior version:** essay-feedback@v6

**Change:** (1) make the filter requirement explicitly declarative — defined under
`resources.retrieval.retrieval_filter` — rather than a code-only convention; (2) add the
runtime-failure scenario; (3) ban post-fetch filtering; (4) specify `on_insufficient: fail`
over silent widening.

The system SHALL filter retrieved rubric exemplars to the submitting student's grade band
before passing them to the generator. Filter is declarative, defined under
`resources.retrieval.retrieval_filter`, and applied at the index-query layer — not post-fetch.

**Rationale.** 11th-grade exemplars shown to a 6th grader on a grief-themed essay was the
precipitating incident. See `docs/postmortems/2026-04-retrieval-filter-leak.md`. Post-fetch
filtering is explicitly disallowed because an exhausted candidate pool silently degraded the
top-k below the floor and the symptom was invisible in logs.

#### Scenario: 6th grader submits a narrative essay
- **Given** a submission from `grade_band: 6-8`
- **When** the retriever is invoked against `resources.retrieval.index`
- **Then** every retrieved exemplar SHALL have metadata `grade_band ∈ {6-8}`
- **And** top-k SHALL equal `resources.retrieval.top_k` (no silent reduction)
- **And** if fewer than top-k candidates match, the handler SHALL raise
  `InsufficientExemplars` and return HTTP 503 rather than fall back to a broader band.

#### Scenario: Retrieval filter missing at runtime
- **Given** a request where the resolved `retrieval_filter` is null
- **Then** the handler SHALL raise `RetrievalFilterMissing` before calling the index
- **And** SHALL return HTTP 500 with no model invocation
- **And** SHALL emit `retrieval_filter_missing` at CloudWatch priority `ERROR`.
