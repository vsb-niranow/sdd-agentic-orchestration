# ADR 0004 — Separate `debug_resources:` block, not a widened `resources:`

- **Status:** Accepted (2026-09-05)
- **Proposal:** `add-debug-resources-block`

## Context

See `docs/postmortems/2026-09-jit-too-narrow.md`. During a production
throttling event, on-call couldn't tail Bedrock invocation logs because
the capability's `resources:` block didn't list the log group.

Options considered:

1. Widen `resources:` to include debuggability resources.
2. Create a standing cluster-admin role for on-call.
3. Add a separate `debug_resources:` block scoped only to debugging.

## Decision

Option 3. `debug_resources:` is a distinct, optional block in the spec
schema. It's recognized by the JIT broker in `--mode debug` only, vended
with TTL ≤ 2h, requires an on-call attestation JWT, and is restricted to
read-only actions on CloudWatch log groups, X-Ray traces, and Bedrock
invocation logs.

## Consequences

**Positive.**
- Production access stays minimal. `resources:` is still the narrow runtime
  surface.
- Debug access is specced, auditable, and time-boxed. Every vend is logged
  with the proposal ID.
- No standing admin roles. The organization's IAM finding count on
  standing roles went from "pervasive" to "zero on capabilities using this
  pattern."

**Negative.**
- Two blocks to maintain. Capability authors learn when to put what where.
  Convention: if it's read-only and only humans need it, it goes in
  `debug_resources:`. If a Lambda needs it, it goes in `resources:`.
- JIT broker has two code paths (`prod` and `debug`). Tested; contained.
- On-call attestation requires an on-call rotation API. We already had
  one for paging; integration was small.

## Why not just read-only everywhere?

Considered allowing `resources:` to have per-action access-level enums
("read" vs "read_write"). Rejected because it conflates two concerns:
runtime access (deterministic, specified once per capability) and
operator access (situational, needs attestation + TTL). Keeping them
separate is clearer and keeps the JIT broker's logic simple enough to
reason about.
