# ADR 0001 — OpenSpec as the single pipeline entry

- **Status:** Accepted (2026-01-10)
- **Supersedes:** None
- **Superseded by:** None

## Context

The team was debating where "a feature begins." Historical options:

- **Jira ticket.** Author writes a story; developer writes code; code review
  catches gaps. Standard. The problem: Jira custom fields are weak as a
  policy substrate, and security + privacy reviewers are not reliably in the
  loop.
- **Design doc.** Author writes a Google Doc; design review decides; Jira is
  derived. The problem: the design doc is unversioned and detaches from the
  code the moment implementation starts. Spec drift is guaranteed.
- **OpenSpec change proposal in the monorepo.** Author writes markdown with
  machine-readable blocks; downstream tooling reads it; Jira, IAM, lint, and
  AI reviewer all key off the same artifact.

## Decision

OpenSpec change proposals under `openspec/changes/<id>/` are the single
entry point for every feature. No feature exists in Jira until a proposal
is merged. No IAM role is vended without a spec. No code review is run
"from scratch" — always against the delta.

## Consequences

**Positive.**
- Audit is trivial: every production line of code → PR → change ID → spec
  version. District procurement reviewers loved this; it was the fastest
  procurement conversation we had.
- Onboarding dropped from ~3 weeks to ~1. The spec folder is the onboarding
  doc.
- Security sign-off moved from a weekly meeting to automated OPA checks on
  80%+ of changes. Security team now looks at the hard 20%.

**Negative.**
- Learning curve. New engineers need to internalize the spec-first flow
  before they're productive. The first week is specs, not code.
- Spec authoring is a real skill. Humans who are good at it ship 3–4×
  faster than humans who aren't. This is a real inequality we're still
  working on with onboarding material.
- Tooling investment is upfront. The OPA bundle, Jira-MCP, JIT broker, and
  AI reviewer collectively were ~6 weeks of platform work before any
  feature benefited. The return came quickly after.

## Why not GitHub Issues + a docs folder?

Considered. Rejected because Issues don't live in the repo commit graph,
and the audit chain is weakest at the issue layer (anyone can edit an
issue anytime). The proposal-in-repo keeps the audit chain intact.
