# Design notes — add-essay-feedback-v1

Design notes are for alternatives considered and tradeoffs taken. Not normative; the spec is.
Claude Code is told to consult `design.md` only when the spec is genuinely silent — most
disagreements with the generated code have been resolved by tightening the spec, not by
expanding the design doc.

## Model choice

**Chosen:** Bedrock Claude Sonnet 4.6 (`anthropic.claude-sonnet-4-6-20260815-v1:0`).

- Haiku 4.5 benchmarked within 3 points of Sonnet on `rubric_alignment_v1` but refused borderline
  essays 2.1× more often. For teacher-facing feedback the refusal rate matters more than the raw
  score — teachers lose trust in a product that refuses one in ten submissions.
- Opus was too expensive for the 8s p95 budget and marginal quality (1.4 points above Sonnet,
  within the regression tolerance).
- GPT-4o-equivalents were evaluated but rejected on BAA / FERPA grounds.

## Why temperature 0.2

- 0.0 produced identical feedback across student essays with high surface similarity (common
  rubric targets). Teachers flagged it as "canned."
- 0.2 produced enough lexical variation to feel individualized without destabilizing the
  structured JSON output. 0.3+ increased malformed JSON rate to 3.8% from 0.4%.

## Why reject widening retrieval filter

See EF-SR-003 Scenario 1. The product manager initially pushed for "if we can't find 5 exemplars
at grade band, show 4 from the adjacent band — some guidance is better than failing." Rejected
because:
1. The adjacent band is where the 2026-04 incident originated (6th → 11th exemplar leak).
2. The caller (`essay-feedback`) can opt into widening explicitly via spec — but opting IN is a
   per-capability deliberate choice, not a default.
3. The fail-mode is louder than the silent-degradation mode. Loud fails get fixed.

## Cost model

Expected volume: 1.2M submissions/mo across pilot districts at GA. Average 3,200 input tokens +
900 output tokens per submission. At Sonnet 4.6 prices this is about $14k/mo. Circuit breaker
at $50k/mo (10× headroom) — above this threshold the capability returns HTTP 429 and surfaces to
teachers "come back in a few minutes," which they prefer to a cost outage.

## What we considered and deferred

- **Multi-rubric support.** Each district has 3–7 rubric variants. V1 ships narrative only.
  Deferred to `add-essay-feedback-rubric-expansion` (post-2026-Q2).
- **Streaming responses.** Teacher UI would be better with token streaming. Deferred — the eval
  harness is simpler against full responses. Measured product harm is low because the full
  response is < 8s.
- **Teacher override.** Teacher edits the feedback before sharing with the student. Deferred to
  `teacher-review-ui`. The data model (feedback_id as immutable artifact + teacher overlay as
  separate record) is forward-compatible.
