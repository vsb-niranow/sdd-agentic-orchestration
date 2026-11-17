# Spec Schema (reference)

Normative definition lives at `openspec/specs/spec-schema/spec.md` — this doc is a readable
summary with examples. If the two disagree, the spec wins.

## File layout

A capability spec is a single markdown file at `openspec/specs/<capability>/spec.md` with:

1. A YAML frontmatter header (machine-readable).
2. A `## Purpose` section (prose, one paragraph).
3. A `## Requirements` section containing one `### Requirement: <ID> — <title>` per SHALL.
4. A `## Non-Goals` section with a bulleted list.
5. A `## Resources` section — a fenced ```yaml block``` — this is what JIT IAM and OPA consume.
6. An `## Eval Contract` section (another fenced yaml block).

Every delta proposal at `openspec/changes/<id>/specs/<cap>/spec.md` uses the same body shape but
wraps requirements in `## ADDED Requirements`, `## MODIFIED Requirements`, or
`## REMOVED Requirements` so the merge job can compute diff semantics.

## Frontmatter fields

```yaml
---
capability: essay-feedback              # required; matches folder name
version: 7                              # required; monotonic integer
breaking: false                         # required; OPA routes approvals
owners:                                 # required; GitHub teams
  - "@niranow/applied-ai"
  - "@niranow/platform"
pii_class: 2                            # required for student-touching caps
retention: 90d                          # required; enum (see project.md)
status: active                          # active | deprecated | retired
supersedes: []                          # list of prior spec filenames
---
```

OPA rejects a file whose frontmatter is missing any required field.

## Requirement block

```markdown
### Requirement: EF-SR-003 — Grade-band retrieval filter

The system SHALL filter retrieved rubric exemplars to the submitting student's grade band
before passing them to the generator.

**Rationale.** 11th-grade exemplars shown to a 6th grader on a grief-themed essay was the
precipitating incident. See `docs/postmortems/2026-04-retrieval-filter-leak.md`.

#### Scenario: 6th grader submits a narrative essay
- **Given** a submission from `grade_band: 6-8`
- **When** the retriever is invoked against `index: rubric_exemplars_v12`
- **Then** every retrieved exemplar has metadata `grade_band ∈ {6-8}`
- **And** top-k is capped at `resources.retrieval.top_k`

#### Scenario: Retrieval filter missing
- **Given** a request where the resolved `retrieval_filter` is null
- **Then** the handler SHALL raise `RetrievalFilterMissing` and return HTTP 500
- **And** the request SHALL NOT fall back to unfiltered retrieval
```

**Rules:**
- The ID line (`### Requirement: ID — title`) is parsed by regex. Do not alter the format.
- At least one `#### Scenario:` is required. Multiple are encouraged; one per equivalence class
  of input.
- `Given / When / Then / And` bullets are expected. The AI reviewer extracts preconditions and
  postconditions by parsing these bullets.
- `**Rationale.**` is optional but strongly encouraged — it's what gives the AI reviewer and the
  next engineer the "why."

## Resources block

```yaml
resources:
  model:
    provider: bedrock
    arn: arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6-20260815-v1:0
    inference_profile_arn: arn:aws:bedrock:us-east-1:111122223333:inference-profile/us.claude-sonnet-4-6
    temperature: 0.2
    max_output_tokens: 1200
    stop_sequences: ["</feedback>"]
  prompts:
    - id: essay_feedback@v7
    - id: rubric_exemplar_rerank@v2
  retrieval:
    index: arn:aws:aoss:us-east-1:111122223333:collection/rubric-exemplars-prod
    embedding_model: amazon.titan-embed-text-v2:0
    top_k: 5
    min_similarity: 0.72
    retrieval_filter:
      kind: grade_band_match
      source_field: submission.grade_band
      target_field: exemplar.grade_band
  storage:
    submissions_bucket: arn:aws:s3:::niranow-ela-submissions-prod
    feedback_table: arn:aws:dynamodb:us-east-1:111122223333:table/essay-feedback-prod
  observability:
    cloudwatch_namespace: NiraNow/EssayFeedback
    # debug_resources vended separately — see docs/adr/0004-debug-resources-block.md
```

JIT IAM reads this block, resolves each ARN to the minimal action set (template in
`tools/jit-iam-broker/action_templates.yaml`), and vends a role with TTL ≤ `resources.ttl` (default
4h production, 2h for `debug_resources`).

## Eval contract

```yaml
eval:
  set_id: rubric_alignment_v3
  threshold: 0.82                  # minimum mean score across cases to pass CI
  metric: rubric_alignment_blended # defined in evals/<set>/manifest.yaml
  isolation: strict                # forbids overlap with any retrieval index
  regression_tolerance: 0.02       # ship-blocking if score drops > this vs. baseline
```

`isolation: strict` is enforced by `policy/opa/eval_isolation.rego` — OPA cross-references the
eval set's `source_documents` against every capability's `resources.retrieval.index`. Any
intersection fails the gate.

## Non-goals

```markdown
## Non-Goals

- This capability does NOT translate student writing. Language detection + translation is a
  separate capability (`language-router`).
- This capability does NOT persist drafts. Draft lifecycle belongs to the client.
- This capability does NOT score grammar as a standalone output. Rubric scoring is the output.
```

The AI reviewer uses this list to decide whether un-specced code paths are scope creep (e.g.,
Claude Code added a `translate()` helper "because it was convenient") or legitimate internals.

## Delta semantics

A proposal's delta file at `openspec/changes/<id>/specs/<cap>/spec.md`:

```markdown
## ADDED Requirements

### Requirement: EF-GR-004 — Retrieval filter guardrail
… (full requirement block)

## MODIFIED Requirements

### Requirement: EF-SR-003 — Grade-band retrieval filter
**Prior version:** essay-feedback@v6
**Change:** now requires `min_similarity ≥ 0.72` (was 0.65). Scenarios updated.
… (full new requirement block, overwrites prior)

## REMOVED Requirements

### Requirement: EF-SR-001
**Reason:** superseded by EF-SR-003 after retrieval filter guardrail added.
```

The merge job:
1. Parses the golden spec into a map keyed by SHALL ID.
2. Applies ADDED (insert, must be new ID), MODIFIED (replace, must be existing ID), REMOVED
   (delete, mark retired).
3. Bumps the capability's `version:` by 1.
4. Writes the new golden spec and updates `openspec/CHANGELOG.md`.
5. Triggers the Jira-MCP → OPA → JIT chain.
