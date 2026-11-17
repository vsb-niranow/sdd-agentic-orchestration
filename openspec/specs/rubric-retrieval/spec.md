---
capability: rubric-retrieval
version: 4
breaking: false
owners:
  - "@niranow/applied-ai"
pii_class: 1
retention: 90d
status: active
supersedes:
  - rubric-retrieval@v1
---

## Purpose

Retrieve rubric exemplars from the `rubric-exemplars-prod` OpenSearch Serverless collection,
filtered to the requesting capability's declared `retrieval_filter`, with a reranking pass that
boosts exemplars from matching district tenants and genre tags.

This capability is called by `essay-feedback` (and, in the future, by any capability that grounds
a generation on rubric exemplars). It owns retrieval policy; callers own what they do with the
results.

## Requirements

### Requirement: RR-SR-001 — Filter is declarative and applied at query time

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

### Requirement: RR-SR-002 — Insufficient candidates → fail, don't widen

If the filtered k-NN query returns fewer than `top_k` candidates and the caller's spec declares
`retrieval_filter.on_insufficient: fail`, the retriever SHALL raise `InsufficientExemplars`.
Widening the filter (relaxing the grade band, dropping the genre match) is never permitted
without a spec-declared `on_insufficient: widen_to: <profile>`.

#### Scenario: Only 3 exemplars for grade 11-12 on a specific rubric
- **Given** `top_k: 5`, `on_insufficient: fail`, and filtered results = 3
- **Then** the retriever SHALL raise `InsufficientExemplars` with `returned: 3, required: 5`.

#### Scenario: Caller opts into widening
- **Given** `on_insufficient: widen_to: adjacent_band`
- **And** 3 exemplars matched exactly
- **Then** the retriever MAY query again with `grade_band ∈ {6-8, 9-10}` to reach `top_k`
- **And** SHALL return a per-result metadata tag `source_band: <band>` so the caller can
  surface the widening in logs.

### Requirement: RR-SR-003 — Embedding model pinned

The retriever SHALL use `resources.embedding_model` for query embedding. The model ID at
runtime SHALL be compared to the spec value at startup; drift fails startup.

### Requirement: RR-SR-004 — Rerank uses a separate, versioned prompt

If a caller requests `rerank: true`, the retriever SHALL invoke the Bedrock model via the
prompt `rubric_exemplar_rerank@v2`. The rerank prompt SHALL NOT be bundled into the generation
prompt — it is a distinct model call with its own token budget.

### Requirement: RR-SR-005 — Index-vs-eval-set isolation enforced at startup

At startup, the retriever SHALL verify that `resources.retrieval.index` is NOT listed as a
source for any eval set with `isolation: strict`. If it is, the retriever SHALL refuse to start.

**Rationale.** Few-shot overlap with the eval set drove a silent 4-point drop between CI scores
and production. See `docs/postmortems/2026-06-eval-leakage.md`. Runtime enforcement is in
addition to OPA enforcement at merge time — defense in depth.

#### Scenario: Startup overlap detection
- **Given** `rubric-exemplars-prod` is listed as a source for `rubric_alignment_v3`
- **And** `rubric_alignment_v3.isolation: strict`
- **Then** the retriever SHALL fail to start and emit `eval_isolation_violation` at `CRITICAL`.

### Requirement: RR-GR-001 — Exemplars are classified content

The retriever SHALL NEVER return exemplar content without the index's `content_classification`
metadata field. The field feeds the caller's output content filter.

### Requirement: RR-NR-001 — Observability

Every retrieval SHALL emit `retrieval_latency_ms`, `candidates_returned`,
`filter_rejected_count`, `rerank_latency_ms` (if rerank invoked), and `widen_used` (bool).

## Non-Goals

- This capability does NOT own exemplar authoring or indexing. Index population is a batch
  pipeline in `data-ingest/rubric-exemplars` (not specced here).
- This capability does NOT serve exemplars to end users. It is an internal API.
- This capability does NOT implement its own caching layer. Caching is OpenSearch-native.

## Resources

```yaml
resources:
  model:
    provider: bedrock
    arn: arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0
    inference_profile_arn: arn:aws:bedrock:us-east-1:111122223333:inference-profile/us.claude-haiku-4-5
    temperature: 0.1
    max_output_tokens: 300
  prompts:
    - id: rubric_exemplar_rerank@v2
  retrieval:
    index: arn:aws:aoss:us-east-1:111122223333:collection/rubric-exemplars-prod
    embedding_model: amazon.titan-embed-text-v2:0
    top_k: 5
    min_similarity: 0.72
    retrieval_filter:
      kind: grade_band_match
      source_field: submission.grade_band
      target_field: exemplar.grade_band
      on_insufficient: fail
  storage: null
  observability:
    cloudwatch_namespace: NiraNow/RubricRetrieval
    log_group: /aws/lambda/rubric-retrieval-prod
  ttl: 4h
```

## Eval Contract

```yaml
eval:
  set_id: retrieval_precision_v2
  threshold: 0.78
  metric: recall_at_5_with_filter
  isolation: strict
  regression_tolerance: 0.03
```
