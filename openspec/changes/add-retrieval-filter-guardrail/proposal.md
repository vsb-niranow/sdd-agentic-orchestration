---
change_id: add-retrieval-filter-guardrail
capability: multi             # affects spec-schema + essay-feedback + rubric-retrieval
author: "@b-v-srujana"
reviewers:
  - "@niranow/platform"
  - "@niranow/privacy"
  - "@niranow/security"
proposal_date: 2026-04-12
status: merged
merge_date: 2026-04-16
breaking: true                # tightens the schema; existing RAG specs become invalid until amended
postmortem_ref: docs/postmortems/2026-04-retrieval-filter-leak.md
---

## Summary

Make `retrieval_filter:` a **schema-required field** on any capability that declares
`resources.retrieval.index`. Previously, retrieval filtering was a capability-level choice —
`essay-feedback@v1` implemented it, but the schema did not require it. The 2026-04 incident
showed that this was a latent gap waiting to activate on any new RAG capability.

## Why

On 2026-04-07 a 6th-grade student submitted an essay on bereavement. The retrieval filter that
restricted exemplars to the `6-8` grade band had been implemented in the first Claude Code
generation of `essay-feedback` — but when we added a new experimental capability
(`rubric-genre-match`) three sprints later, Claude Code generated it without a retrieval filter
because the **spec didn't require one**. The experimental capability was behind a flag that got
flipped in the wrong district config and the student was shown an 11th-grade exemplar quoting a
graphic scene. Not illegal content, but inappropriate for the band and emotionally mismatched.

The fix is not "remember to add the filter next time." The fix is making the filter impossible
to omit:

1. Add `SS-SR-006` to the spec-schema: RAG capabilities require a declared `retrieval_filter`.
2. Add a top-level OPA policy `retrieval_filter.rego` that rejects any merged capability spec
   where `resources.retrieval.index != null` and `resources.retrieval.retrieval_filter` is
   missing or null.
3. Update `essay-feedback`'s `EF-SR-003` scenario to include a "retrieval filter missing at
   runtime" case — we want runtime failure, not runtime silent passthrough, if the filter is
   somehow stripped by a deployment accident. Defense in depth.
4. Update `rubric-retrieval`'s `RR-SR-001` — the filter MUST be applied at the query layer, not
   post-fetch. Post-fetch filtering degraded top-k silently in the incident; making it a query-
   layer requirement forces the index-side failure mode (empty candidate set → explicit error).

## What this proposal does NOT do

- Does not remove `retrieval_filter` from `essay-feedback` — that filter already exists. This
  proposal promotes it from capability-specific to schema-required.
- Does not add a policy for widening fallbacks. That's a separate design discussion; see
  `design.md`.

## Backward compatibility

Breaking at the schema layer. Existing RAG specs that don't declare a filter will fail OPA on
their next edit. Grace period: 7 days to backfill. During the grace window, OPA emits warnings
instead of rejections (feature-flagged in `policy/opa/spec_validation.rego` under
`retrieval_filter_grace_until`).

## Rollout

1. Merge this proposal. Schema change is picked up by OPA on next bundle rebuild (~15 min).
2. Open follow-up PRs on every existing RAG capability to backfill `retrieval_filter:`.
3. Flip `retrieval_filter_grace_until` to past date — enforcement hardens.
4. Backfill the AI reviewer's "un-specced behavior" training examples with the incident's
   generated code so the reviewer learns to flag the pattern.
