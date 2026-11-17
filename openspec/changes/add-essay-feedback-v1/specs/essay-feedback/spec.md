## ADDED Requirements

### Requirement: EF-SR-001 — Submission accepted

The system SHALL accept a submission consisting of `student_id`, `assignment_id`, `grade_band`
(enum: `6-8 | 9-10 | 11-12`), `rubric_id`, and `essay_text` (≤ 8,000 Unicode characters after
NFC normalization). (Full scenarios in the golden spec.)

### Requirement: EF-SR-002 — Rubric-aligned output structure

The feedback output SHALL be a JSON object with one top-level key per rubric dimension declared
in the resolved `rubric_id`. (Full structure in the golden spec.)

### Requirement: EF-SR-003 — Grade-band retrieval filter

The system SHALL filter retrieved rubric exemplars to the submitting student's grade band before
passing them to the generator.

> **Note at v1 merge time (2026-01-22):** this requirement is enforced at the capability's code
> layer but is NOT yet schema-required across all RAG capabilities. That cross-cutting change
> arrives in `add-retrieval-filter-guardrail` after the 2026-04 incident.

### Requirement: EF-SR-004 — Prompt binding through registry

The handler SHALL resolve every prompt by `prompt_id@version` through `prompts/registry.yaml`.

### Requirement: EF-SR-005 — Model invocation pinned

The handler SHALL invoke the model identified by `resources.model.arn` only.

### Requirement: EF-GR-001 — Output content filter for grade band

Before returning feedback, the capability SHALL run output through the content filter defined
by `guardrails.output_content_filter`.

### Requirement: EF-GR-002 — PII redaction in logs

The capability SHALL redact `student_id` and the full `essay_text` from all logs, traces, and
metrics dimensions.

### Requirement: EF-GR-003 — Off-topic refusal

If the model's internal relevance score falls below `0.4`, the capability SHALL return a refusal
payload.

### Requirement: EF-NR-001 — Observability

Every request SHALL emit the metrics enumerated in the golden spec.

### Requirement: EF-PR-001 — Enqueue latency

p95 handler-to-enqueue latency SHALL be ≤ 100ms.

### Requirement: EF-AR-001 — Readable feedback

`feedback_text` SHALL target a Flesch–Kincaid grade level ≤ the student's `grade_band` upper
bound.
