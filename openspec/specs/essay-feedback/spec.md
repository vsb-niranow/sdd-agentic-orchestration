---
capability: essay-feedback
version: 7
breaking: false
owners:
  - "@niranow/applied-ai"
  - "@niranow/ela-product"
pii_class: 2
retention: 90d
status: active
supersedes:
  - essay-feedback@v1
  - essay-feedback@v4
---

## Purpose

Generate rubric-aligned written feedback on a 6–12 student essay. Given a submission and the
district's rubric variant, the capability retrieves grade-band-appropriate exemplars, calls
Bedrock Claude with a versioned prompt, and returns feedback structured per rubric dimension. The
output is persisted for the student's teacher to review and optionally share back.

This is the product's revenue-generating capability. Every other capability in this repo exists
to make this one safe, measurable, or auditable.

## Requirements

### Requirement: EF-SR-001 — Submission accepted

The system SHALL accept a submission consisting of `student_id`, `assignment_id`, `grade_band`
(enum: `6-8 | 9-10 | 11-12`), `rubric_id`, and `essay_text` (≤ 8,000 Unicode characters after
NFC normalization).

#### Scenario: Valid submission under character limit
- **Given** `grade_band: 6-8` and `essay_text` of 4,500 chars
- **When** the handler receives the request
- **Then** the handler SHALL return HTTP 202 with a `feedback_id`
- **And** SHALL enqueue the request for processing within 100ms (see EF-PR-001).

#### Scenario: Submission over character limit
- **Given** `essay_text` of 8,001 chars after NFC normalization
- **Then** the handler SHALL return HTTP 413 `EssayTooLong` with `max_chars: 8000` in the body
- **And** SHALL NOT enqueue the submission
- **And** SHALL NOT invoke the model.

#### Scenario: Unknown rubric_id
- **Given** `rubric_id` not present in the district's rubric catalog
- **Then** the handler SHALL return HTTP 404 `UnknownRubric` with the submitted `rubric_id`.

### Requirement: EF-SR-002 — Rubric-aligned output structure

The feedback output SHALL be a JSON object with one top-level key per rubric dimension declared
in the resolved `rubric_id`. Each dimension's value is an object:

```
{
  "score": <int 1..4>,
  "feedback_text": <string, ≤ 600 chars>,
  "evidence_spans": [{"start": <int>, "end": <int>, "quote": <string>}],
  "next_step": <string, ≤ 200 chars>
}
```

#### Scenario: Four-dimension narrative rubric
- **Given** a `rubric_id` resolving to dimensions `[ideas, organization, voice, conventions]`
- **When** feedback is generated
- **Then** the response object SHALL have exactly those four top-level keys (no more, no less)
- **And** every `score` SHALL be an integer in `1..4`
- **And** every `evidence_spans[*].start, end` SHALL be valid offsets into the submitted essay
  (0 ≤ start < end ≤ len(essay_text)).

#### Scenario: Evidence span out of range
- **Given** the model returns a span with `end: 9500` on a 4,500-char essay
- **Then** the post-processor SHALL clip the span to the essay length and emit a CloudWatch
  metric `invalid_evidence_span_count`
- **And** SHALL NOT fail the request.

### Requirement: EF-SR-003 — Grade-band retrieval filter

The system SHALL filter retrieved rubric exemplars to the submitting student's grade band before
passing them to the generator. Filter is declarative, defined under
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
- **Given** a request where the resolved `retrieval_filter` is null (e.g., misconfigured
  deploy)
- **Then** the handler SHALL raise `RetrievalFilterMissing` before calling the index
- **And** SHALL return HTTP 500 with no model invocation
- **And** SHALL emit `retrieval_filter_missing` at CloudWatch priority `ERROR`.

### Requirement: EF-SR-004 — Prompt binding through registry

The handler SHALL resolve every prompt by `prompt_id@version` through
`prompts/registry.yaml`. Prompt text SHALL NOT appear as a string literal in the handler, the
retriever, or the IaC. Content hash of the resolved prompt SHALL be logged alongside every
model invocation for auditability.

#### Scenario: Correct prompt resolution
- **Given** `resources.prompts[0].id: essay_feedback@v7`
- **When** the handler starts
- **Then** it SHALL read `prompts/registry.yaml`, resolve to `prompts/essay_feedback_v7.md`,
  compute its SHA-256
- **And** fail-fast with `PromptHashMismatch` if the registry's recorded hash does not match
  the file's current hash.

#### Scenario: Inline prompt literal detected by lint
- **Given** source code containing a string that looks like a prompt system message
- **Then** the `prompts_in_code.py` lint rule SHALL fail the build with the line number.

### Requirement: EF-SR-005 — Model invocation pinned

The handler SHALL invoke the model identified by `resources.model.arn` only. On startup the
handler SHALL verify that the configured ARN matches the spec's pinned ARN; on mismatch it
SHALL refuse to start.

**Rationale.** Bedrock foundation models are published as versioned artifacts, but inference
profiles are mutable. We had one incident where an inference profile was retargeted to a newer
model mid-release and feedback regressed silently. We now pin both the ARN and the inference
profile; the inference profile's backing model is verified by a startup probe.

#### Scenario: Inference profile backing drifts
- **Given** `resources.model.inference_profile_arn` resolves to a model ARN different from
  `resources.model.arn`
- **Then** the handler SHALL fail to start and emit `model_pin_drift` at priority `CRITICAL`.

### Requirement: EF-GR-001 — Output content filter for grade band

Before returning feedback, the capability SHALL run output through the content filter defined
by `guardrails.output_content_filter` (grade-band-aware) and SHALL replace or regenerate any
dimension whose `feedback_text` triggers a hit.

#### Scenario: 6th-grade feedback contains a flagged reference
- **Given** generated feedback whose `voice.feedback_text` contains a reference flagged for the
  6-8 band
- **When** the output filter runs
- **Then** the capability SHALL regenerate `voice` (once; bounded retry) with a temperature of
  `max(resources.model.temperature - 0.05, 0.0)`
- **And** if the retry also hits the filter, the capability SHALL substitute a canned fallback
  from `prompts/essay_feedback_v7_fallbacks.md` and emit `fallback_voice_6_8_used`.

### Requirement: EF-GR-002 — PII redaction in logs

The capability SHALL redact `student_id` and the full `essay_text` from all logs, traces, and
metrics dimensions. Only the SHA-256 of the essay (truncated to 12 hex chars) MAY appear.

#### Scenario: Error path doesn't bypass redaction
- **Given** a model-invocation exception
- **When** the error is logged
- **Then** the stack trace SHALL be scrubbed by the `pii_scrubber` middleware before write
- **And** a sampled random essay substring SHALL NOT be attached to the error even for
  debuggability — use the hash to correlate with an opt-in debug store.

### Requirement: EF-GR-003 — Off-topic refusal

If the model's internal relevance score (`relevance_score` extracted from the model's structured
output) falls below `0.4`, the capability SHALL return a refusal payload instructing the teacher
to review the submission manually — not fabricated rubric feedback.

#### Scenario: Student submits a non-essay
- **Given** a submission consisting of song lyrics with no connection to the assignment prompt
- **When** the model returns `relevance_score: 0.11`
- **Then** the capability SHALL return HTTP 200 with
  `{"refused": true, "reason": "off_topic", "teacher_action_required": true}`.

### Requirement: EF-NR-001 — Observability

Every request SHALL emit, at minimum:
- `model_invocation_latency_ms` (p50, p95, p99)
- `retrieval_latency_ms` (p50, p95, p99)
- `exemplars_returned_count` (should equal `top_k`; divergence is a smell)
- `fallback_used` (bool, with dimension = rubric dimension)
- `refused_count` (int)
- `output_token_count` (histogram)

### Requirement: EF-PR-001 — Enqueue latency

p95 handler-to-enqueue latency SHALL be ≤ 100ms. Full end-to-end (submission → persisted
feedback) p95 SHALL be ≤ 8s.

### Requirement: EF-AR-001 — Readable feedback

`feedback_text` SHALL target a Flesch–Kincaid grade level ≤ the student's `grade_band` upper
bound. The eval set `rubric_alignment_v3` includes FK grade level as a scored dimension; drift
beyond `regression_tolerance` fails CI.

## Non-Goals

- This capability does NOT translate student writing. Multilingual support is deferred to
  `language-router` (not yet specced).
- This capability does NOT persist drafts, autosaves, or revision history. Draft lifecycle is a
  client concern.
- This capability does NOT compute a composite / numeric essay score beyond the per-dimension
  1..4 scores. Composite scoring policy varies by district and is out of scope.
- This capability does NOT generate grammar-only feedback. Grammar lives inside rubric
  dimensions (typically `conventions`) — never as a standalone pass.
- This capability does NOT serve parents directly. Parent surfacing is downstream in
  `teacher-review-ui`.

## Resources

```yaml
resources:
  model:
    provider: bedrock
    arn: arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6-20260815-v1:0
    inference_profile_arn: arn:aws:bedrock:us-east-1:111122223333:inference-profile/us.claude-sonnet-4-6-v1
    temperature: 0.2
    max_output_tokens: 1200
    stop_sequences: ["</feedback>"]
  prompts:
    - id: essay_feedback@v7
    - id: rubric_exemplar_rerank@v2
    - id: essay_feedback_v7_fallbacks@v1
  retrieval:
    index: arn:aws:aoss:us-east-1:111122223333:collection/rubric-exemplars-prod
    embedding_model: amazon.titan-embed-text-v2:0
    top_k: 5
    min_similarity: 0.72
    retrieval_filter:
      kind: grade_band_match
      source_field: submission.grade_band
      target_field: exemplar.grade_band
      on_insufficient: fail  # NOT fallback
  storage:
    submissions_bucket: arn:aws:s3:::niranow-ela-submissions-prod
    feedback_table: arn:aws:dynamodb:us-east-1:111122223333:table/essay-feedback-prod
    submissions_kms_key: arn:aws:kms:us-east-1:111122223333:key/9e5a0e3a-1234-5678-abcd-ef0123456789
  tenant_config_ref:
    table: arn:aws:dynamodb:us-east-1:111122223333:table/tenant-config-prod
    partition_key: district_id
  observability:
    cloudwatch_namespace: NiraNow/EssayFeedback
    log_group: /aws/lambda/essay-feedback-prod
  guardrails:
    output_content_filter: grade_band_appropriate_v3
    pii_scrubber: default_v2
    refusal_threshold: 0.4
  ttl: 4h  # production role TTL
```

## Eval Contract

```yaml
eval:
  set_id: rubric_alignment_v3
  threshold: 0.82
  metric: rubric_alignment_blended   # blend: dimension_match 0.4 + evidence_grounded 0.3 + fk_grade_appropriate 0.2 + refusal_precision 0.1
  isolation: strict
  regression_tolerance: 0.02
  baseline_run: evals/rubric_alignment_v3/baselines/2026-10-01_v6.json
```
