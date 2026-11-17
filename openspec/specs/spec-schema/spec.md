---
capability: spec-schema
version: 11
breaking: false
owners:
  - "@niranow/platform"
  - "@niranow/applied-ai"
pii_class: 0
retention: none
status: active
supersedes: []
---

## Purpose

Define the structural contract that every capability spec in this repo MUST satisfy so that
downstream consumers — the Jira-MCP server, the OPA bundle, the JIT IAM broker, spec-aware lint,
and the AI reviewer — can read and reason about specs without needing a human in the loop.

This is a **meta-capability**. It specifies the shape of other specs. Changes here are breaking
by nature even when the `breaking:` flag is false, because every capability spec is downstream.

## Requirements

### Requirement: SS-SR-001 — Required frontmatter fields

Every capability spec SHALL begin with a YAML frontmatter block declaring, at minimum: `capability`,
`version` (monotonic integer), `breaking`, `owners`, `pii_class`, `retention`, `status`.

#### Scenario: Missing a required field
- **Given** a spec file missing `pii_class`
- **When** OPA evaluates the spec
- **Then** OPA returns `violation` with rule `spec_validation.required_frontmatter`
- **And** the Jira-MCP server SHALL block the resulting story until the field is added.

#### Scenario: `pii_class` not an integer in 0..3
- **Given** `pii_class: "high"`
- **Then** OPA SHALL reject with `spec_validation.pii_class_enum`.

### Requirement: SS-SR-002 — SHALL ID format

Every requirement in a capability spec SHALL carry an ID matching the regex
`^[A-Z]{2,3}-(SR|GR|NR|PR|AR)-\d{3}$`. IDs are globally unique within a capability and are never
reused across the capability's lifetime.

#### Scenario: Reused ID after removal
- **Given** `EF-SR-001` was removed in a prior proposal
- **When** a new proposal attempts to add `EF-SR-001`
- **Then** OPA SHALL reject with `spec_validation.shall_id_reuse` and cite the retiring commit.

### Requirement: SS-SR-003 — At least one scenario per requirement

Every `### Requirement:` block SHALL be followed by at least one `#### Scenario:` sub-block
containing `Given / When / Then` bullets.

**Rationale.** The AI reviewer extracts preconditions and postconditions by parsing scenario
bullets. A requirement without a scenario is not testable, which is why `shall_id_coverage` lint
would also fail — but we enforce at the OPA layer too so humans can't merge an un-scenarioed
requirement even if lint hasn't run yet.

#### Scenario: Requirement without a scenario
- **Given** a requirement block with no `#### Scenario:` child
- **Then** OPA SHALL reject with `spec_validation.scenario_missing`.

### Requirement: SS-SR-004 — Machine-readable `resources:` block

Every capability spec that calls external systems SHALL include a `## Resources` section
containing a single fenced YAML block. The block MUST validate against the schema at
`policy/opa/schemas/resources.schema.json`.

#### Scenario: Model ARN unpinned
- **Given** `resources.model.arn` ending in `:latest` or without a version suffix
- **Then** OPA SHALL reject with `model_pinning.not_pinned`.

### Requirement: SS-SR-005 — Retention is an enum

Retention declarations SHALL use one of: `none | 30d | 90d | district_configured`. Prose values
are rejected.

**Rationale.** First merged proposal said "retained per district policy." OPA couldn't interpret
it. False-rejection rate on retention dropped near zero once we moved to enums. See
`docs/postmortems/2026-02-opa-ambiguous-retention.md`.

#### Scenario: Prose retention
- **Given** `retention: "per district policy"`
- **Then** OPA SHALL reject with `pii_retention.enum_required`.

### Requirement: SS-SR-006 — RAG capabilities require `retrieval_filter:`

Any capability whose `resources.retrieval.index` is set SHALL also declare
`resources.retrieval.retrieval_filter` (object, not null).

**Rationale.** Retrieval filter was once implicit. See
`docs/postmortems/2026-04-retrieval-filter-leak.md`. The schema no longer permits implicit.

#### Scenario: RAG without retrieval filter
- **Given** a capability spec with `resources.retrieval.index` but no `retrieval_filter`
- **Then** OPA SHALL reject with `retrieval_filter.required`.

### Requirement: SS-SR-007 — Eval contract with threshold

Every capability spec that invokes a model SHALL declare `## Eval Contract` with: `set_id`,
`threshold` (float in 0..1), `metric` (defined in the eval set's manifest), and `isolation`
(enum: `strict | advisory | none`).

#### Scenario: Eval threshold missing
- **Then** OPA SHALL reject with `spec_validation.eval_threshold_missing`.

#### Scenario: `isolation: none` on PII-touching capability
- **Given** `pii_class >= 2` and `eval.isolation: none`
- **Then** OPA SHALL reject with `eval_isolation.required_for_pii`.

### Requirement: SS-SR-008 — Explicit `non_goals`

Every spec SHALL include a `## Non-Goals` section with ≥ 1 bulleted entry. The entry may be
`- (none at this time)` for genuinely scopeless capabilities, but the section must exist.

**Rationale.** The AI reviewer flags un-specced behavior as either scope creep or legitimate
internals based on whether it is covered under `non_goals`. An absent section defaults to "any
behavior not covered by a SHALL is scope creep" — too strict, blocks reasonable glue code.

### Requirement: SS-SR-009 — `breaking:` flag at frontmatter root

`breaking: true` is required for: adding/removing a SHALL requirement (SR-kind), changing an
existing SHALL's acceptance scenarios in a way that would fail a prior-passing test,
removing/renaming a resource ARN, lowering an eval threshold, or changing a retention enum to a
shorter value.

`breaking: false` is permitted for: adding non-SR requirements (GR/NR/PR/AR) that are
additive-only, raising an eval threshold, extending (not shortening) retention, adding
`debug_resources:` entries, adding `non_goals`.

#### Scenario: Breaking change flagged non-breaking
- **Given** a proposal that removes a SHALL ID and declares `breaking: false`
- **Then** OPA SHALL reject with `approval_routing.breaking_flag_wrong`.

### Requirement: SS-SR-010 — Delta files use ADDED/MODIFIED/REMOVED sections

A change proposal's spec delta at `openspec/changes/<id>/specs/<cap>/spec.md` SHALL contain
exactly the sections required to express the diff: zero or more of `## ADDED Requirements`,
`## MODIFIED Requirements`, `## REMOVED Requirements`. The delta file SHALL NOT include the full
golden body.

#### Scenario: Delta file contains golden body
- **Given** a delta file with a top-level `## Purpose` section
- **Then** the merge job SHALL reject with `spec_validation.delta_shape`.

## Non-Goals

- This spec does NOT define how downstream tools *implement* their validators. Each consumer owns
  its own validator; this spec defines only the shape they consume.
- This spec does NOT define the markdown style guide (line length, heading casing). That lives
  in `docs/markdownlint.yaml`.
- This spec does NOT define Jira custom fields. Those live in the Jira-MCP server's config.

## Resources

```yaml
# This capability is pure schema. It owns no AWS resources.
resources:
  model: null
  prompts: []
  retrieval: null
  storage: null
  observability:
    cloudwatch_namespace: NiraNow/SpecSchema
```

## Eval Contract

```yaml
eval:
  set_id: spec_schema_fuzz_v2
  threshold: 1.0                 # every case must pass; schema is strict
  metric: parse_succeeds
  isolation: none                # no retrieval, nothing to leak
  regression_tolerance: 0.0
```
