# Postmortem — Eval leakage / CI-vs-prod score divergence (2026-06-15)

**Severity:** P2 (no student impact; silent quality regression in production)

**Affected capability:** `essay-feedback`

**Spec delta that resolved it:** `add-eval-isolation-policy` (merged
2026-06-21).

## Summary

For roughly 6 weeks the `essay-feedback` production rubric alignment score
(sampled from teacher re-ratings) sat ~4 points below the CI eval score
that had been shipping green. On investigation: the OpenSearch collection
`rubric-exemplars-prod` had been seeded with 47 documents that overlapped
with the eval set `rubric_alignment_v3`'s test cases. Few-shot retrieval
was pulling the eval's own cases into context, which made the model look
better in CI than in production.

## Timeline

- **~2026-05-01** — Data-ingest batch mistakenly included the 47
  teacher-authored exemplars from the eval set. No one noticed; the
  documents were legitimate exemplars with correct grade-band metadata.
- **2026-05 → 2026-06** — Every PR's eval score ran against partially
  memorized retrievals. Scores held ≥ 0.83 consistently. We shipped 4
  `essay-feedback` tune-* proposals in that window; all passed CI.
- **2026-06-14** — Teacher ratings for the 3rd pilot district came in. Mean
  rating 0.79 against a CI-measured 0.84. Four-point gap → investigation.
- **2026-06-15** — Correlation analysis showed retrieval IDs in the
  production trace overlapped the eval set's source documents.
- **2026-06-15 EOD** — Documents removed from the production index.
- **2026-06-18** — `add-eval-isolation-policy` proposal opened.
- **2026-06-21** — Merged.
- **2026-06-23** — Post-cleanup baseline captured for
  `rubric_alignment_v3`. Dropped from 0.843 to 0.806. Follow-up
  `tune-essay-feedback-threshold-post-isolation` opened (threshold stayed
  at 0.82 — the model was genuinely close).

## Root cause

**Human:** The data-ingest pipeline had no awareness of which documents
were in which eval set's source list. An ops engineer bulk-uploaded
teacher-authored exemplars (good!) without cross-referencing eval sources.

**Technical:** The spec schema did not require declaring eval isolation.
`eval.isolation` as a field didn't exist.

## Contributing factors

1. CI and production ran against different index populations. The CI index
   was a frozen snapshot from late-April; prod drifted after. Any time CI
   diverges from prod composition, this failure mode exists.
2. No alert on "CI score + regression tolerance > prod rating by margin X".
   We shipped this as a follow-up (`observability-ci-vs-prod-drift`, not in
   this folder's scope).
3. The eval harness's isolation check (EH-SR-002 added later) did not exist
   to catch it at run time.

## What changed

1. **Spec schema:** `SS-SR-007` (modified) — `eval.isolation` is now a
   required enum (`strict | advisory | none`). Default-strict for PII caps.
2. **OPA:** `eval_isolation.rego` cross-references every merged capability's
   retrieval index against the eval set's source documents. Overlap →
   deny (strict) or warn (advisory).
3. **Eval harness:** `EH-SR-002` — runtime check before invoking a case.
4. **Rubric-retrieval:** `RR-SR-005` — startup probe to catch out-of-band
   mutation of the index after merge.

## What did not change

- The eval set itself. Source documents were already declared in the eval
  set's manifest — the enforcement was missing, not the data.
- The production index. The 47 overlap documents were removed and
  replaced with non-eval-set teacher exemplars authored during the
  cleanup.

## Why defense in depth here

Three layers: OPA at merge, eval-harness at run time, retriever at startup.
The index is a live mutable store; merge-time checks alone are insufficient
because an index can drift after merge. Startup + runtime enforcement
catches drift. Yes, it's redundant. Redundancy is the point.
