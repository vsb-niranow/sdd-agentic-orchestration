# Tasks — add-essay-feedback-v1

Jira-MCP reads this file and creates one story per `- [ ]` top-level checkbox. Sub-bullets become
story description; `(EF-SR-###)` references stamp the Jira custom field `openspec_shall_id`.

## 1. Handler scaffold
- [ ] Emit the Lambda handler at `services/essay-feedback/handler.py`
  - Binds inputs per EF-SR-001
  - Resolves prompt_id through `prompts/registry.yaml`
  - Verifies model ARN pinning at startup (EF-SR-005)
  - Wires in `pii_scrubber` middleware (EF-GR-002)

## 2. Retrieval integration
- [ ] Implement retrieval client in `services/essay-feedback/retrieval.py`
  - Calls `rubric-retrieval` capability (RR-SR-001, RR-SR-002)
  - Surfaces `InsufficientExemplars` to the handler as HTTP 503 (EF-SR-003)
  - Emits `exemplars_returned_count` metric

## 3. Prompt binding
- [ ] Implement prompt binder in `services/essay-feedback/prompting.py`
  - Reads from `prompts/registry.yaml`
  - Fails fast on hash mismatch (EF-SR-004)
  - Attaches content-hash to CloudWatch log fields

## 4. Guardrails
- [ ] Output content filter (EF-GR-001) — `services/essay-feedback/guardrails.py`
  - Uses `grade_band_appropriate_v3`
  - Bounded retry (1) on filter hit
  - Falls back to canned response on second hit
- [ ] Off-topic refusal (EF-GR-003)
  - Extracts `relevance_score` from model output
  - Returns refusal payload below threshold

## 5. Response structure
- [ ] Post-processor in `services/essay-feedback/response.py`
  - Validates evidence spans into essay bounds (EF-SR-002)
  - Clips rather than fails on out-of-range spans
  - Emits `invalid_evidence_span_count`

## 6. IaC
- [ ] Terraform under `services/essay-feedback/iac/`
  - All ARNs read verbatim from `resources:` block
  - Lambda, DynamoDB table, S3 bucket, CloudWatch log group, KMS CMK
  - IAM role scoped via JIT broker's generated policy (see JIT output under
    `.jit/artifacts/<change-id>.json`)

## 7. Evals
- [ ] Generate eval runner at `services/essay-feedback/evals/runner.py`
  - Loads `evals/rubric_alignment_v3/manifest.yaml`
  - Enforces threshold ≥ 0.82
  - Fails CI on regression > 0.02 vs. baseline

## 8. Tests
- [ ] One test file per SHALL ID: `tests/test_essay_feedback_<id>.py`
  - Covers at least one Scenario per Requirement block
  - Named `test_<cap>_<shall_id>_<scenario_slug>`

## 9. Observability
- [ ] Emit all metrics from EF-NR-001
- [ ] CloudWatch dashboard `NiraNow-EssayFeedback-Prod` with the required panels
