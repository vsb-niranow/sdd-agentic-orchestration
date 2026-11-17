# OpenSpec changelog

Updated by the merge job. One entry per merged proposal, in reverse
chronological order. Human edits forbidden (CI enforces).

## 2026-09-05 — `add-debug-resources-block`
**Capability:** spec-schema (v10 → v11)
**Breaking:** false
**Why:** On-call could not tail CloudWatch during a Bedrock throttling incident.
Introduces `debug_resources:` block, 2h TTL, read-only. See postmortem
`2026-09-jit-too-narrow.md`.

## 2026-08-18 — `tighten-prompt-spec-coupling`
**Capability:** spec-schema (v9 → v10)
**Breaking:** false
**Why:** A latency hotfix edited a prompt without a spec delta; the AI
reviewer then flagged unrelated PRs. CI now requires prompt files and
their owning capability spec delta in the same commit. See
`2026-08-prompt-drift-hotfix.md`.

## 2026-06-21 — `add-eval-isolation-policy`
**Capabilities:** spec-schema (v8 → v9), eval-harness (v2 → v3),
rubric-retrieval (v3 → v4)
**Breaking:** true (eval contract now requires `isolation:`)
**Why:** Eval set documents had been seeded into the production retrieval
index; CI scores sat 4 points above production ratings. `eval.isolation`
enum enforced by OPA at merge, harness at run time, retriever at startup.
See `2026-06-eval-leakage.md`.

## 2026-04-16 — `add-retrieval-filter-guardrail`
**Capabilities:** spec-schema (v7 → v8), essay-feedback (v6 → v7),
rubric-retrieval (v2 → v3)
**Breaking:** true (RAG caps without `retrieval_filter:` are invalid;
7-day backfill grace)
**Why:** A 6th grader was shown an 11th-grade exemplar. Schema now
requires explicit `retrieval_filter:` on every RAG capability. See
`2026-04-retrieval-filter-leak.md`.

## 2026-02-11 — [implicit] retention enum
**Capability:** spec-schema (v6 → v7)
**Breaking:** false
**Why:** OPA rejected ~40% of early proposals over ambiguous prose
retention. Moved to enum. See `2026-02-opa-ambiguous-retention.md`.

## 2026-01-22 — `add-essay-feedback-v1`
**Capability:** essay-feedback (v0 → v1)
**Breaking:** true (new capability)
**Why:** First capability. Rubric-aligned feedback for 6–8 band narrative
rubric. Pilot to 3 districts behind a feature flag.
