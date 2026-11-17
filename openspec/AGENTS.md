# Agent conventions

Two agents operate inside this pipeline. Both have narrow roles.

## 1. The implementer agent (Claude Code)

Reads: merged spec, `design.md`, `CLAUDE.md`, the IAM role vended by JIT.

Writes: implementation code under `services/<cap>/`, IaC under
`services/<cap>/iac/`, tests under `services/<cap>/tests/`, eval runners,
CloudWatch dashboards.

Must not:

- Author or edit spec files.
- Inline prompt text.
- Hard-code model ARNs.
- Request IAM permissions not declared in `resources:` or `debug_resources:`.
- "Improve" the design during implementation. If the spec is wrong, halt
  and request a delta.

See `CLAUDE.md` in the repo root for the full contract.

## 2. The reviewer agent (different provider)

Reads: golden spec, delta, candidate diff.

Writes: findings JSON. Does not write code. Does not approve PRs.

Enforcement:

- `REVIEWER_PROVIDER` env var must not equal `anthropic` when the
  implementer is Claude Code. CI job verifies.
- Reviewer's `temperature` is 0.0. Non-determinism in review is a bug.

See `tools/ai-reviewer/prompts/spec_diff_reviewer_v2.md`.

## Human-in-the-loop seams

- **Proposal merge** — humans only.
- **Breaking change approval** — platform team only.
- **OPA policy edit** — platform + security.
- **PR merge** — human reviewer after AI reviewer findings cleared.
- **JIT debug-mode vend** — on-call attestation JWT required.

The agents are powerful glue. The humans own the contract.
