## ADDED Requirements

### Requirement: SS-SR-012 — Prompt changes require a spec delta in the same commit

Any PR whose diff touches a file matching `prompts/**/*.md` SHALL also contain a modified file
at `openspec/changes/<id>/specs/<cap>/spec.md` for the capability that owns the touched prompt.
Ownership is resolved through `prompts/registry.yaml`.

**Rationale.** A latency hotfix once edited a prompt without bumping the version or updating
the spec, which caused the AI reviewer to flag unrelated PRs. See
`docs/postmortems/2026-08-prompt-drift-hotfix.md`.

#### Scenario: Prompt change without spec delta
- **Given** a PR that modifies `prompts/essay_feedback_v7.md` only
- **Then** CI SHALL fail with `prompt-delta-coupling: orphan prompt change`
- **And** the annotation SHALL cite the owning capability (`essay-feedback`) and the exact
  spec-delta path the author must create or amend.

#### Scenario: Prompt registry hash mismatch
- **Given** `prompts/registry.yaml` records `essay_feedback_v7.sha256: abc123…`
- **And** the on-disk file hashes to `def456…`
- **Then** `tools/spec-lint/rules/prompt_registry_coherent.py` SHALL fail with
  `prompt_registry_coherent: hash mismatch for essay_feedback_v7 (expected abc123…, got
  def456…)`.
