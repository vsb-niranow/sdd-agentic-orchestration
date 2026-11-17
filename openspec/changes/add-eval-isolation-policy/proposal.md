---
change_id: add-eval-isolation-policy
capability: multi             # spec-schema + eval-harness + rubric-retrieval
author: "@b-v-srujana"
reviewers:
  - "@niranow/platform"
  - "@niranow/applied-ai"
proposal_date: 2026-06-18
status: merged
merge_date: 2026-06-21
breaking: true
postmortem_ref: docs/postmortems/2026-06-eval-leakage.md
---

## Summary

Add `eval.isolation: strict | advisory | none` to the spec schema. Enforce `strict` by cross-
referencing the capability's `resources.retrieval.index` against every eval set's declared
`source_documents`. Any intersection fails OPA — and fails the retriever's startup probe, as
defense in depth.

## Why

On 2026-06-15 we noticed `essay-feedback`'s production rubric alignment score (sampled from
teacher re-ratings) sat about 4 points below the CI eval score that had been shipping green. On
investigation: the OpenSearch collection `rubric-exemplars-prod` had been seeded with the same
sample essays that the eval set `rubric_alignment_v3` used as test cases. Few-shot retrieval
was pulling the eval's own cases into context, making the model look great in CI.

The code change is trivial — exclude those 47 documents from the index. The pipeline change is
the real fix: make this impossible to re-introduce. The spec declares the eval set; the eval set
declares its source documents; OPA enforces that no capability's retrieval index intersects an
eval set's source documents for any `isolation: strict` eval. The retriever also probes at
startup and refuses to start on overlap.

## What this proposal does NOT do

- Does not change eval case authoring process. Cases still live in `evals/<set>/cases/`.
- Does not re-run baselines. The capability spec amendments are separate PRs that will bump
  thresholds once post-cleanup baselines are measured.

## Backward compatibility

Breaking: existing specs without `eval.isolation:` fail OPA on next edit. Default is `strict`
for `pii_class >= 1`, `advisory` for `pii_class == 0`. A capability can opt out to `none` only
with platform-team sign-off, routed by `approval_routing.rego`.

## Rollout

1. Merge proposal → OPA bundle picks up new rule.
2. Author backfill PRs on `essay-feedback`, `rubric-retrieval`, `eval-harness`.
3. Cleanup PR on the index: remove the 47 overlap documents.
4. Re-run baselines on `rubric_alignment_v3`; expect ~4-point drop.
5. Open a follow-up proposal to adjust capability thresholds if post-cleanup baseline falls
   below current threshold.
