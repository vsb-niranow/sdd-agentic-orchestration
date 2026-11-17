# ADR 0003 — Reviewer model is a different provider than the implementer

- **Status:** Accepted (2026-02-14)

## Context

Early in the project, Claude Code was both writing and (self-)reviewing the
implementation. On paper this works — the reviewer agent has a different
system prompt focused on scope and spec adherence. In practice we observed
that Claude Code's reviewer persona had systematic blind spots exactly
matching Claude Code's implementer persona. "The retrieval filter was
there, I remember checking" was a common failure mode that produced an
internally consistent but externally wrong review.

## Decision

The AI reviewer is explicitly a **different provider** than the
implementer. Claude Code writes the code; a GPT-4-class or Gemini-class
model reviews it. This is enforced by environment variable
(`REVIEWER_PROVIDER`) and verified in the GitHub Action's job matrix.

## Consequences

**Positive.**
- Catches a class of errors that would survive same-provider review. The
  2026-04 retrieval filter incident would not have been caught by Claude
  Code reviewing Claude Code; the reviewer's system prompt would have
  reasoned "the filter is implied in the retrieval context" the same way
  the implementer did. The different-provider reviewer caught similar
  patterns on subsequent PRs.
- The reviewer's findings are worth attending to; they aren't just "Claude
  Code echoing itself."

**Negative.**
- Extra integration. We maintain two model-vendor relationships, two API
  keys, two rate limits, and (currently) two billing lines.
- Review quality depends on the reviewer model being roughly capability-
  equivalent to the implementer. If the reviewer is dramatically weaker,
  its findings become noisy. We hold a soft rule: reviewer's eval score on
  the `ai_reviewer_meta_v2` set must be within 5 points of the
  implementer's to be permitted as reviewer.
- Different-provider reviewers may themselves have systematic biases
  (over-flagging politically sensitive content, for example). We tune the
  reviewer's system prompt to exclude those categories explicitly.

## Why not two providers both writing, one reviewing?

Considered — a "consensus write" approach where two providers each emit
code and a judge picks. Rejected because: (a) the Jira audit chain
expects one implementer per story; (b) the cost is 2× the implementation
budget; (c) empirically, one competent implementer + one skeptical
different-provider reviewer caught more errors per dollar than
consensus-write. If reviewer costs continue to drop, we may revisit.
