---
change_id: add-essay-feedback-v1
capability: essay-feedback
author: "@b-v-srujana"
reviewers:
  - "@niranow/platform"
  - "@niranow/ela-product"
  - "@niranow/privacy"
proposal_date: 2026-01-14
status: merged
merge_date: 2026-01-22
breaking: true          # introduces a new capability + new resource ARNs
---

## Summary

Introduce the `essay-feedback` capability — the core revenue-generating behavior of the AI
writing-feedback assistant. This proposal is the capability's v1 and is deliberately scoped to
production-shippable minimum: single rubric (district-authored narrative), 6–8 band only, English
only, no refusal handling beyond a naive relevance threshold.

## Why now

District procurement for the three pilot districts closes 2026-02-28. Pilot contracts require
"rubric-aligned feedback on student essays, grade-band-appropriate," which is satisfied by this
v1 if we ship the retrieval filter and the eval harness alongside. Broader bands (9-10, 11-12),
multiple rubric types, and language support are explicit follow-ups and tracked in `design.md`.

## What this proposal does NOT do

- Does not add the `retrieval_filter:` schema requirement. That comes after the 2026-04 incident
  and is a separate proposal (`add-retrieval-filter-guardrail`). This v1 ships with retrieval
  filtering implemented but not **schema-required** — a lesson we'd later encode as policy.
- Does not define eval isolation. That comes from the 2026-06 incident.
- Does not define `debug_resources:`. That's from the 2026-09 incident.

Each of those is a separate proposal in this folder.

## Rollout

1. Shadow mode for 2 weeks: feedback generated but not shown to students. Teachers rate samples.
2. Pilot to 3 districts behind feature flag `essay_feedback_v1_enabled`.
3. GA when eval score ≥ 0.80 on `rubric_alignment_v1` AND teacher rating ≥ 4.0/5 on 500 samples.

## Risks

- **Model cost blow-out.** Bedrock Sonnet 4.6 on 8k input + 1.2k output is expensive. Mitigation:
  circuit-breaker at 10× budgeted volume; see `design.md` §Cost.
- **Over-reliance on retrieval filter correctness.** If the filter misfires we expose
  grade-inappropriate content. Mitigation: output content filter as a second line. (The
  2026-04 incident later showed this mitigation was insufficient — see the delta proposal.)
- **Prompt drift.** Someone edits `essay_feedback_v7.md` without a spec change. Mitigation
  deferred — becomes the `tighten-prompt-spec-coupling` proposal after we were burned.
