---
capability: eval-harness
version: 3
breaking: false
owners:
  - "@niranow/applied-ai"
  - "@niranow/platform"
pii_class: 1
retention: 90d
status: active
supersedes:
  - eval-harness@v1
---

## Purpose

Run a capability's declared eval set on every PR and on every model/prompt change, enforce the
spec-declared threshold, and publish a per-case report the AI reviewer and humans can consume.
Prevent silent model regressions from shipping.

## Requirements

### Requirement: EH-SR-001 — One eval run per capability per PR

For every PR that touches a capability spec, a prompt file referenced by that capability, or
source under `services/<capability>/`, the harness SHALL run the capability's declared eval set
(`eval.set_id` in the spec) against the candidate build.

#### Scenario: Prompt-only change
- **Given** a PR that changes `prompts/essay_feedback_v7.md`
- **And** the prompt is referenced by capability `essay-feedback`
- **Then** the harness SHALL run `rubric_alignment_v3` against the candidate build
- **And** block merge if `score < threshold` OR `score < baseline - regression_tolerance`.

### Requirement: EH-SR-002 — Isolation enforced at run time

Before invoking a case, the harness SHALL verify that none of the case's `source_documents`
appears in any live retrieval index listed in the capability's `resources.retrieval.index` when
the capability's `eval.isolation == strict`.

#### Scenario: Eval case document found in production index
- **Given** case `case_042` has `source_documents: [exemplar_017]`
- **And** `exemplar_017` is present in `rubric-exemplars-prod`
- **Then** the harness SHALL abort the run and emit `eval_leakage_detected` at `CRITICAL`.

### Requirement: EH-SR-003 — Baseline comparison

The harness SHALL compare the candidate's score against the baseline recorded at
`eval.baseline_run` and fail the PR if `candidate_score < baseline_score -
regression_tolerance`.

### Requirement: EH-SR-004 — Report structure

The harness SHALL emit a report JSON containing: `capability`, `set_id`, `candidate_score`,
`baseline_score`, `threshold`, per-case `{case_id, score, passed, trace_id}`, and a GitHub-
compatible summary markdown. The AI reviewer consumes this JSON directly.

### Requirement: EH-SR-005 — Trace reproducibility

Every case run SHALL store the exact model input (post-retrieval, post-prompt-binding), the
exact model output, and the scoring function's output in an S3 artifact under
`s3://niranow-eval-artifacts/<capability>/<pr_id>/<case_id>.json`. Retention is 30d; artifacts
older than 30d are tombstoned, hashes kept for audit.

### Requirement: EH-GR-001 — PII never written to eval artifacts

Eval cases are curated — they MAY contain student-shaped text but SHALL NOT contain real
`student_id` values. The harness SHALL reject any case whose `source_documents` contain a value
matching the `student_id_regex` from `policy/opa/schemas/pii.yaml`.

## Non-Goals

- The harness does NOT define scoring metrics. Metrics are per-eval-set, defined in
  `evals/<set>/manifest.yaml`.
- The harness does NOT author eval cases. Case authoring is manual + templated; lives in
  `evals/<set>/cases/`.
- The harness is NOT a load/stress tester. It evaluates quality, not latency under load.

## Resources

```yaml
resources:
  model:
    provider: bedrock
    arn: arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6-20260815-v1:0
    inference_profile_arn: arn:aws:bedrock:us-east-1:111122223333:inference-profile/us.claude-sonnet-4-6-v1
    temperature: 0.0
    max_output_tokens: 1500
  prompts: []
  retrieval: null
  storage:
    artifacts_bucket: arn:aws:s3:::niranow-eval-artifacts
    artifacts_kms_key: arn:aws:kms:us-east-1:111122223333:key/eval-artifacts-cmk
  observability:
    cloudwatch_namespace: NiraNow/EvalHarness
    log_group: /aws/lambda/eval-harness
  ttl: 2h  # CI-time; shorter than production
```

## Eval Contract

```yaml
eval:
  set_id: eval_harness_meta_v1   # evals that test the harness itself
  threshold: 1.0                 # every meta-case must pass
  metric: run_matches_expected
  isolation: none
  regression_tolerance: 0.0
```
