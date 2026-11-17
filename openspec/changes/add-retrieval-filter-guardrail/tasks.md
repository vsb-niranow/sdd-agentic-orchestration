# Tasks — add-retrieval-filter-guardrail

## 1. Schema change
- [ ] Amend `openspec/specs/spec-schema/spec.md`
  - Add `SS-SR-006`: RAG capabilities require `retrieval_filter:`
  - Add scenario: "RAG without retrieval filter → OPA rejects"
  - Bump schema version 10 → 11

## 2. OPA policy
- [ ] Author `policy/opa/retrieval_filter.rego`
  - Rule: `deny[msg]` if `resources.retrieval.index != null` and `resources.retrieval.retrieval_filter == null`
  - Rule: `warn[msg]` during grace window
- [ ] Unit tests in `policy/opa/retrieval_filter_test.rego`
  - Case: explicit filter present → allow
  - Case: null filter + RAG index → deny
  - Case: no RAG index → allow
  - Case: grace window active + null filter → warn, not deny

## 3. `essay-feedback` tightening
- [ ] Amend `openspec/specs/essay-feedback/spec.md` EF-SR-003
  - Add runtime-failure scenario
  - Explicitly disallow post-fetch filtering
  - Bump capability version 6 → 7

## 4. `rubric-retrieval` tightening
- [ ] Amend `openspec/specs/rubric-retrieval/spec.md` RR-SR-001
  - Make query-layer filtering a SHALL, not a SHOULD
  - Bump capability version 3 → 4

## 5. Spec-lint rule
- [ ] Add `tools/spec-lint/rules/retrieval_filter_declared.py`
  - Keyed off SS-SR-006
  - Mirrors OPA at the local-dev layer (fails pre-push, not just at merge)

## 6. AI reviewer rule
- [ ] Add reviewer directive to `tools/ai-reviewer/prompts/spec_diff_reviewer_v2.md`
  - Flag any code path that queries a RAG index without applying the spec's
    `retrieval_filter` object

## 7. Postmortem artifact
- [ ] Publish `docs/postmortems/2026-04-retrieval-filter-leak.md`
  - Include detection path, timeline, remediation, and the schema change this proposal makes

## 8. Grace window
- [ ] Set `retrieval_filter_grace_until = 2026-04-23` in the OPA bundle
- [ ] Calendar reminder to flip to past date on 2026-04-23
