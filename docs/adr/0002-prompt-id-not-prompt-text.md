# ADR 0002 — Prompts are referenced by ID, never inlined

- **Status:** Accepted (2026-01-10; tightened in `tighten-prompt-spec-coupling`
  2026-08-18)

## Context

Early drafts of the essay-feedback spec included the prompt text inside the
spec. Felt natural — "the spec says what the model does, the prompt is what
the model does." Three problems surfaced within a sprint:

1. The spec got enormous. A 2,000-token prompt inside a 1,000-word spec
   made the spec unreadable.
2. Prompt edits became spec edits requiring privacy sign-off every time.
   Prompt engineers were blocked waiting for the wrong reviewers.
3. The AI reviewer couldn't diff prompt changes semantically — it saw a
   wall of text in the spec change and either flagged every word or
   flagged nothing.

## Decision

- Prompts live in `prompts/<id>_v<N>.md`.
- `prompts/registry.yaml` maps `<id>@v<N>` to a file + sha256.
- Capability specs reference `prompt_id@v<N>`. They do not contain prompt
  text.
- Any prompt file change requires a spec delta in the same commit
  (enforced by `.github/workflows/prompt-delta-coupling.yaml`), but the
  delta only needs to bump the version reference — the full new text is in
  the prompt file.

## Consequences

**Positive.**
- Specs stayed reviewable. Humans could read them.
- Prompt engineering became a first-class versioned artifact with its own
  eval governance (every prompt file change triggers the owning
  capability's eval set).
- AI reviewer could short-circuit on hash mismatch; semantics only run
  against a coherent prompt.

**Negative.**
- Two-file-coupling is overhead. CI enforces it; developers occasionally
  forget. The error message is explicit about the fix path, which
  mitigates the friction.
- Prompt files are their own privacy-reviewed artifact. The owning
  capability's CODEOWNERS include `@niranow/privacy` for exactly this
  reason.

## Why not store prompts in DynamoDB or S3?

Considered. Rejected because the prompt's audit chain belongs in git. If
a prompt lives outside the commit graph, we lose the "every production
line traces to a commit" property. Prompt files in git, hash-checked
against the registry, is the cheapest way to keep that chain intact.
