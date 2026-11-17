# Postmortem — Prompt drift during a latency hotfix (2026-08-10)

**Severity:** P3 (no student impact; eroded trust in the AI reviewer)

**Affected capability:** `essay-feedback` (prompt v7)

**Spec delta that resolved it:** `tighten-prompt-spec-coupling` (merged
2026-08-18).

## Summary

During a Bedrock latency spike, an engineer shortened
`prompts/essay_feedback_v7.md` to reduce input tokens. They did not bump the
version to v8. They did not update `prompts/registry.yaml`. They did not
open a spec delta. The change merged as an isolated prompt-file edit.

For the next ~90 minutes the AI reviewer flagged "un-specced prompt
behavior" on every subsequent unrelated PR, because the prompt's content
hash no longer matched the spec's declared version. Reviewers lost trust
in the reviewer and started paging platform to ask whether the reviewer
was broken. The real failure was that we allowed a prompt change to merge
without its spec delta.

## Timeline

- **2026-08-10 22:40 UTC** — Bedrock latency spike, p95 to ~14s.
- **2026-08-10 22:51 UTC** — Engineer A opens PR #4821 trimming the prompt
  by ~30% of its tokens. Spec-lint fires `prompt_registry_coherent` but
  the error was interpreted as a cosmetic one; they updated the sha in the
  registry in the same PR but did not bump the version.
- **2026-08-10 23:05 UTC** — PR merged to unblock latency. Latency
  recovered.
- **2026-08-10 23:32 UTC** — Unrelated PR #4823 triggers AI reviewer. The
  reviewer's short-circuit prompt-hash check passes (registry is coherent)
  but the reviewer agent itself notices the prompt's semantics drifted and
  flags "un-specced output format behavior." Confusing.
- **2026-08-11 00:11 UTC** — Platform paged. The git blame on
  `essay_feedback_v7.md` revealed the hotfix. Rolled forward (we kept the
  shorter prompt) but opened the `tighten-prompt-spec-coupling` proposal.
- **2026-08-18** — Proposal merged.

## Root cause

**Human:** Hotfix pressure led to skipping the version bump and the spec
delta. The engineer who wrote the hotfix knew these were best practices;
they explicitly reasoned "the latency problem is urgent, we'll clean this
up tomorrow." Tomorrow didn't happen because the fix worked and nobody
remembered.

**Technical:** No CI rule enforced that a prompt file change must be
accompanied by a spec delta. The `prompt_registry_coherent` lint rule
catches hash drift, but the engineer updated the hash in the same PR —
so the rule passed.

## What changed

1. **Spec schema:** `SS-SR-012` — prompt file changes require a spec delta
   in the same commit. OPA enforces at merge.
2. **CI:** `.github/workflows/prompt-delta-coupling.yaml` — GitHub Action
   that computes the ownership of each changed prompt file and enforces
   the coupling.
3. **AI reviewer:** short-circuits on prompt hash mismatch with a specific
   error class (`prompt_hash_mismatch`) instead of running semantic
   analysis. Semantics against a drifted prompt are meaningless and
   confusing.

## Why we didn't just forbid prompt-only PRs

Considered. Rejected because legitimate prompt-only PRs do exist —
reverting a failed experiment, say. The right rule is "a prompt change is
a spec change, write both." Forbidding prompt changes entirely would push
people to in-code prompt literals (the exact failure mode `prompt_id_pinned`
catches).

## The real lesson

**Spec drift is a red build, not a backlog item.** Before this incident we
treated "someone forgot to update the spec" as technical debt. Now it is
a CI failure. Drift basically stopped once we made it a build-stop; the
rate of "spec says X, code does Y" findings from the AI reviewer dropped
from a steady ~2/week to effectively zero.
