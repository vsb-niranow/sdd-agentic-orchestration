# Architecture

## System view

```
   human              GitHub repo              downstream tooling
     │                    │                           │
     │ 1. open PR          │                           │
     │  (proposal)         │                           │
     ▼                     │                           │
  ┌───────┐                │                           │
  │ Draft │                │                           │
  │ PR    │                │                           │
  └───┬───┘                │                           │
      │ 2. CI: spec-lint   │                           │
      │                     │                           │
      ▼                     │                           │
  ┌──────────────────┐     │                           │
  │ spec-lint.yaml    │────┤                           │
  │ runner.py         │     │                           │
  └───────────────────┘     │                           │
      │ 3. human merges     │                           │
      │                      │                           │
      ▼                      │                           │
  ┌──────────────────────┐  │                           │
  │  merge → main         │──┤                           │
  └───────────────────────┘  │                           │
      │                       │                           │
      ▼                       │                           │
  ┌─────────────────────┐    │       ┌──────────────┐    │
  │  opa-gate.yaml       │────┼──────▶│ OPA bundle   │    │
  │  evaluates proposal  │    │       │ policy/opa/  │    │
  │  against policy      │◀───┼───────│   *.rego      │    │
  └─────────────────────┘    │       └──────────────┘    │
      │ pass                   │                           │
      ▼                       │                           │
  ┌─────────────────────┐    │       ┌──────────────┐    │
  │ Jira-MCP webhook     │────┼──────▶│ Jira         │    │
  │ reads tasks.md →     │    │       └──────────────┘    │
  │ creates epic+stories │    │                           │
  └─────────────────────┘    │                           │
      │                       │                           │
      ▼                       │                           │
  ┌─────────────────────┐    │       ┌──────────────┐    │
  │ JIT IAM broker        │────┼──────▶│ AWS IAM      │    │
  │ reads resources:      │    │       │ time-boxed   │    │
  │ vends role            │    │       │ role         │    │
  └─────────────────────┘    │       └──────────────┘    │
      │                       │                           │
      ▼                       │                           │
  ┌─────────────────────┐    │                           │
  │ Claude Code           │     │                           │
  │ implementation        │     │                           │
  │ generation            │     │                           │
  └───────┬─────────────┘     │                           │
          │ PR opens          │                           │
          ▼                    │                           │
  ┌─────────────────────┐    │       ┌──────────────┐    │
  │ ai-review.yaml       │────┼──────▶│ reviewer     │    │
  │ different-provider   │    │       │ (OpenAI /    │    │
  │ reviewer agent       │    │       │  Gemini)     │    │
  └───────┬─────────────┘    │       └──────────────┘    │
          │ findings as checks │                           │
          ▼                    │                           │
  ┌─────────────────────┐    │                           │
  │ human reviews PR     │     │                           │
  │ against spec (not    │     │                           │
  │ from scratch)        │     │                           │
  └─────────────────────┘    │                           │
```

## Data flow: a merged proposal

1. **Proposal merged → main.** GitHub Action `opa-gate.yaml` fires.
2. OPA evaluates the proposal against `policy/opa/*.rego`:
   - `spec_validation.rego` — frontmatter fields, SHALL ID format,
     scenario presence, non-goals presence.
   - `model_pinning.rego` — Bedrock ARN pinned; inference profile backing
     matches.
   - `retrieval_filter.rego` — RAG caps declare `retrieval_filter`.
   - `eval_isolation.rego` — no overlap between retrieval index and
     strict-isolation eval set source documents.
   - `pii_retention.rego` — retention is an enum; `district_configured`
     has a `tenant_config_ref`.
   - `debug_resources.rego` — if present, TTL bounds and read-only action
     set.
   - `prompt_versioning.rego` — referenced prompts exist in registry; no
     stale versions.
   - `approval_routing.rego` — correct review teams signed off.
3. On OPA pass, the Jira-MCP webhook creates the epic + stories; story
   custom fields carry the `openspec_proposal_id` and `openspec_shall_ids`.
4. When a developer picks up a story, CI/CD invokes the JIT broker with
   `--mode prod` to vend a time-boxed role scoped to the story's
   capability `resources:` block.
5. Claude Code executes under that role and generates the implementation
   diff. Claude Code's instructions (`CLAUDE.md`) require reading the spec
   first and halting on gaps.
6. On PR open, `spec-lint.yaml` + `prompt-delta-coupling.yaml` +
   `ai-review.yaml` run. The AI reviewer posts findings as check-run
   annotations.
7. Human reviewer opens the PR, reads the AI reviewer's findings, and
   approves or requests changes against the spec.

## What's in the spec, what's in `design.md`

**Spec:** anything a downstream tool consumes — SHALL IDs, scenarios,
resource ARNs, prompt version references, eval set + threshold,
non-goals, `breaking:` flag.

**`design.md`:** alternatives considered, cost modeling, deferred work.
Not consumed by tools. Humans read it to understand *why*.

A good test: if removing the information breaks a CI rule, it belongs in
the spec. If removing it only confuses the next engineer, it belongs in
`design.md`.

## Failure modes we actively defend against

| Failure | Defense |
|---------|---------|
| Spec drift (code says X, spec says Y) | AI reviewer surfaces as `scenario_drift`; human review blocks. |
| Prompt drift (prompt file changes without spec delta) | CI rule `prompt-delta-coupling` + OPA `SS-SR-012`. |
| Model silent version roll | OPA rejects unpinned ARNs; handler verifies at startup. |
| RAG without grade-band filter | OPA `retrieval_filter.rego` + lint + runtime handler check. |
| Eval leakage (test data in retrieval index) | OPA `eval_isolation.rego` + retriever startup probe + harness runtime check. |
| JIT role too narrow for debugging → broader standing role | `debug_resources:` block + attestation-gated vend. |
| Over-broad IAM | JIT broker reads only `resources:`; wildcards are rejected by policy. |
| Ambiguous spec rejected | retention enum + 5 core rules; "if a human must interpret, OPA can't." |
