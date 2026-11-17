# Tasks — add-eval-isolation-policy

## 1. Schema change
- [ ] Amend `openspec/specs/spec-schema/spec.md`
  - Extend SS-SR-007: eval contract now requires `isolation:` enum
  - Add default-strict-for-PII sub-rule

## 2. OPA policy
- [ ] Author `policy/opa/eval_isolation.rego`
  - Loads eval set manifests via data bundle
  - Rejects intersection between a capability's retrieval index and any strict-isolation eval set's source documents
- [ ] Unit tests covering: strict + overlap → deny; strict + no overlap → allow; advisory + overlap → warn; none + overlap → allow with audit record

## 3. Retriever startup probe
- [ ] Amend `openspec/specs/rubric-retrieval/spec.md`
  - Add RR-SR-005 (startup probe)

## 4. Eval harness enforcement
- [ ] Amend `openspec/specs/eval-harness/spec.md`
  - Add EH-SR-002 (isolation enforced at run time)

## 5. Index cleanup
- [ ] Remove the 47 overlap documents from `rubric-exemplars-prod`
- [ ] Capture pre/post baseline for `rubric_alignment_v3`

## 6. Follow-up proposal placeholder
- [ ] If post-cleanup baseline < current threshold, open `tune-essay-feedback-threshold-post-isolation`
