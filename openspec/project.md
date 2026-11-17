# Project Conventions

Loaded into every Claude Code, AI-reviewer, and spec-lint context. Keep it short enough to live
in a prompt; move depth into `docs/`.

## Product domain

**AI writing-feedback assistant** for a 6–12 ELA (English Language Arts) platform. District
customers purchase per-seat licenses. Student essays are submitted, the system retrieves
grade-band- and rubric-appropriate exemplars, and Bedrock Claude generates rubric-aligned
feedback. Student writing is PII-class-2 under our data handling standard (see
`docs/data-classification.md`).

## Capability granularity

- **One capability = one business-visible behavior** with its own eval set, resources, and
  owners. Example capabilities: `essay-feedback`, `rubric-retrieval`, `eval-harness`.
- **One proposal = one capability.** Never bundle. OPA cannot reason about blast radius
  otherwise, and JIT IAM cannot scope the role.
- A capability that ships a cross-cutting schema change (e.g., adding a new required field to
  all RAG specs) splits into: one proposal for the schema change + one follow-up per affected
  capability.

## Spec file layout

Every capability has exactly one file at `openspec/specs/<capability>/spec.md`. That file is the
"golden" post-delta state. Change proposals live at `openspec/changes/<id>/specs/<capability>/
spec.md` and contain **only the delta** (`## ADDED Requirements`, `## MODIFIED Requirements`,
`## REMOVED Requirements`). Applying the delta to the golden spec is what the merge job does.

## SHALL ID format

`<CAP_ABBR>-<KIND>-<NNN>` — e.g. `EF-SR-003` (essay-feedback, Shall-Requirement, number 3),
`EF-GR-001` (essay-feedback, Guardrail, number 1), `RR-SR-004` (rubric-retrieval). KIND is one
of: `SR` (shall requirement), `GR` (guardrail), `NR` (non-functional requirement),
`PR` (performance requirement), `AR` (accessibility requirement).

IDs are stable for the life of the capability. If a SHALL is removed, its ID is retired, never
reused.

## Model + prompt version policy

- Model ARNs are pinned to a specific published version in `resources.model.arn`. No aliases.
  Bedrock inference profiles are permitted only when explicitly listed under
  `resources.model.inference_profile_arn` (the model ARN behind the profile must still be
  pinned).
- Prompts live in `prompts/<id>.md`. The spec references `prompt_id: <id>@vN`. The registry
  (`prompts/registry.yaml`) resolves `<id>@vN` to the content hash. Any change to a prompt file
  requires a version bump and a spec delta in the same commit (enforced by
  `.github/workflows/prompt-delta-coupling.yaml`).

## Retention enums

Prose like "retained per district policy" is rejected by OPA. Only enum values are allowed:

| Value | Meaning |
|-------|---------|
| `none` | Discarded after request completion. Transient only. |
| `30d` | 30 days, then hard delete. |
| `90d` | 90 days, then hard delete. |
| `district_configured` | Honor the district's per-tenant retention value (30–365d). Requires `resources.tenant_config_ref`. |

## Approval routing

OPA routes proposals based on the `breaking:` flag and the touched capability's `owners:`:

- `breaking: false` + non-PII capability → single owner approval.
- `breaking: false` + PII-touching capability → owner + privacy reviewer.
- `breaking: true` → owner + platform-team approval.
- Any proposal that modifies `openspec/specs/spec-schema/spec.md` → platform + privacy + security.

## Owners

See `.github/CODEOWNERS`.
