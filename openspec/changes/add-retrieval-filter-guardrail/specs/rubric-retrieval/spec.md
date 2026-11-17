## MODIFIED Requirements

### Requirement: RR-SR-001 — Filter is declarative and applied at query time

**Prior version:** rubric-retrieval@v3

**Change:** elevate query-layer filtering from SHOULD to SHALL. Add banning-rationale link to
the 2026-04 postmortem. Add explicit non-widening sub-requirement (previously only in
`essay-feedback`).

The retriever SHALL apply `retrieval_filter` at the OpenSearch query layer (via a `filter`
clause in the k-NN query), not as a post-fetch step on returned candidates.

**Rationale.** Post-fetch filtering degrades top-k silently when the candidate pool is sparse.
See `docs/postmortems/2026-04-retrieval-filter-leak.md`.

#### Scenario: Grade-band filter on k-NN query
- **Given** `retrieval_filter.kind: grade_band_match` and submission `grade_band: 6-8`
- **When** the retriever queries OpenSearch
- **Then** the query body SHALL include `{"term": {"grade_band": "6-8"}}` inside the k-NN
  `filter` clause
- **And** SHALL NOT include a broader fallback filter.
