# Postmortem — JIT IAM too narrow for debugging (2026-08-29)

**Severity:** P3 (incident resolution delayed ~40 min; no student impact)

**Affected capability:** `essay-feedback`

**Spec delta that resolved it:** `add-debug-resources-block` (merged
2026-09-05).

## Summary

During a Bedrock throttling event, the on-call engineer could not tail
`/aws/lambda/essay-feedback-prod` logs because the capability spec's
`resources:` block did not list the CloudWatch log group as a resource —
and the JIT broker will not vend a role for anything not in the spec.

The engineer requested a broader role from security. Security correctly
refused ("we don't want to invent a new standing role for debugging").
The engineer worked around it by paging a teammate who happened to have
cluster-admin from a prior role, who tailed on their behalf. Mean time
to resolution was elevated by about 40 minutes.

## Timeline

- **2026-08-29 18:04 UTC** — Bedrock throttling event begins. Capability's
  retry budget exhausts; CloudWatch alarm fires.
- **2026-08-29 18:09 UTC** — Engineer A acks. JIT vends a production role
  scoped to the spec's `resources:` block. Role does not include log
  group read.
- **2026-08-29 18:14 UTC** — Engineer A requests broader role from
  security. Request denied; security correctly notes the right fix is a
  spec change, not a role change.
- **2026-08-29 18:21 UTC** — Engineer A pages Engineer B, who has a
  pre-existing (legacy) cluster-admin role. B tails the logs on A's behalf.
- **2026-08-29 18:46 UTC** — Root cause (Bedrock-side throttling) confirmed.
- **2026-09-02** — `add-debug-resources-block` proposal opened.
- **2026-09-05** — Merged.
- **2026-09-08** — Follow-up `add-essay-feedback-debug-resources` opted
  the capability into the new block.

## Root cause

**Human:** Spec authors (including me) didn't think of log tailing as a
specced resource. We treated `resources:` as "what the Lambda needs at
run time" and forgot that humans operating the Lambda also need defined
access.

**Technical:** No place in the spec schema distinguished "production
runtime access" from "operator debugging access." If an engineer needed
to tail, their only options were (a) violate least privilege by
broadening `resources:` or (b) ask for a standing admin role.

## What changed

1. **Spec schema:** `SS-SR-011` — optional `debug_resources:` block.
   Short TTL (≤ 2h), read-only, resource types restricted to CloudWatch
   log groups, X-Ray traces, and Bedrock invocation logs.
2. **JIT broker:** recognizes `--mode debug`. Requires
   `--oncall-attestation` (signed JWT from the on-call rotation). Vends
   are audit-logged.
3. **OPA:** `debug_resources.rego` — TTL bounds, read-only action set,
   no overlap with production ARNs.

## What this does NOT do

- Does not create standing debug access. Every vend is time-boxed.
- Does not bypass audit. Every vend is logged to the audit stream with
  the on-call attestation payload.
- Does not grant write access. The action templates for debug resource
  types contain only read verbs.

## Why this is the right shape

The alternative was "add a `cluster-admin-emergency` standing role." We
rejected it because standing roles are the single largest source of IAM
findings in our environment. The spec-driven approach forces the
*spec* to be the source of truth for emergency access as much as for
normal access. It also forces every emergency access decision to be
reviewable in a proposal, which maintains the audit chain that district
procurement cares about.
