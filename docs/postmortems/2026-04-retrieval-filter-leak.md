# Postmortem — Retrieval filter leak (2026-04-07)

**Severity:** P1 (student-facing content safety; grade-band mismatch; no
actual harmful content served, but a near-miss)

**Affected capability:** `rubric-genre-match` (experimental, flag-gated)

**Spec delta that resolved it:** `add-retrieval-filter-guardrail` (merged
2026-04-16). Added `SS-SR-006` to the spec-schema; existing capabilities
backfilled during the 7-day grace window.

## Summary

A 6th-grade student submitted a narrative essay about the recent death of a
family member. Through a feature-flagged experimental RAG capability
(`rubric-genre-match`), the student was shown an exemplar paragraph from an
11th-grade essay that contained a graphic bereavement scene. Not illegal.
Not a data breach. But emotionally mismatched, and immediately flagged by
the student's teacher during the beta program.

## Timeline

- **2026-04-07 14:12 ET** — Submission received.
- **2026-04-07 14:12 ET** — Retriever returned 5 candidates, all 11-12 band.
- **2026-04-07 14:12 ET** — Feedback generated with the exemplar quoted
  inline.
- **2026-04-07 14:19 ET** — Teacher reviewed the feedback in the beta
  dashboard, flagged `content_mismatch` with a note.
- **2026-04-07 15:03 ET** — On-call paged. Pulled the flag for the affected
  district within 11 minutes of ack.
- **2026-04-08** — Full on-call review. No other submissions exposed; the
  flag had only rolled to one district that afternoon.
- **2026-04-12** — `add-retrieval-filter-guardrail` proposal opened.
- **2026-04-16** — Proposal merged; grace window set to 7 days.
- **2026-04-23** — Grace window closed; all RAG capabilities had been
  backfilled.

## Root cause

**Human:** Spec schema permitted a RAG capability to omit `retrieval_filter`.
`essay-feedback@v1` implemented the filter in code because the author
remembered. The experimental `rubric-genre-match` capability was generated
by Claude Code from a spec that did not require the filter, and the author
didn't remember to request it.

**Technical:** Nothing failed at runtime. The retriever did exactly what
the spec asked of it — unfiltered k-NN on the index.

## Contributing factors

1. The policy (OPA bundle) was treated as a lagging indicator rather than a
   forcing function. "Gaps in the schema" was on the backlog; the schema is
   the forcing function.
2. The feature flag rolled to a single district without a pre-flight eval
   run against `grade_band_safety` cases — because that eval set didn't
   exist yet. Also added in this proposal.
3. Teacher feedback loop worked within 7 minutes of submission, which is
   excellent, but the student had already seen the content. Teacher review
   is not a prevention; it is a detection.

## What changed

1. **Spec schema:** `SS-SR-006` — RAG capabilities require `retrieval_filter:`.
   OPA enforces at merge. Lint enforces pre-push.
2. **Essay-feedback:** `EF-SR-003` extended with a runtime failure case; the
   handler now fails closed (HTTP 500) if the filter is null at request time.
3. **Rubric-retrieval:** `RR-SR-001` elevated to SHALL; query-layer
   filtering required, post-fetch banned.
4. **New eval set:** `grade_band_safety_v1`. One case per sparse-pool edge.
   Every PR touching a RAG capability runs it.
5. **AI reviewer training:** The reviewer's system prompt now explicitly
   flags "retrieval without filter object" as a short-circuit error class.

## What did not change

- The two-model review architecture (Claude Code writes, different-provider
  reviewer reads) worked as designed — the reviewer at the time didn't flag
  this because the spec didn't require it. The architecture is fine; the
  policy was the gap.
- The experimental flag process. Beta rollouts remain district-scoped.
- The eval harness. It wasn't involved — the harness runs against declared
  cases; this was an emergent run-time behavior that no case covered.
  (That gap is closed by `grade_band_safety_v1`.)

## Why this is the right fix

The alternative we considered was "require code review for every new RAG
capability." That fails for the same reason it always fails: it relies on
humans remembering. The policy approach fails safely — the schema cannot be
circumvented, the lint cannot be skipped, and the OPA bundle is signed and
verified. Any future RAG capability physically cannot merge without a
declared filter. **Spec-driven means the spec is where you solve problems,
not around it.**
