---
change_id: add-debug-resources-block
capability: spec-schema
author: "@b-v-srujana"
reviewers:
  - "@niranow/security"
  - "@niranow/platform"
proposal_date: 2026-09-02
status: merged
merge_date: 2026-09-05
breaking: false
postmortem_ref: docs/postmortems/2026-09-jit-too-narrow.md
---

## Summary

Add an optional `debug_resources:` block to the spec schema and extend the JIT IAM broker to
recognize it. `debug_resources:` grants read-only access to CloudWatch log groups, X-Ray
traces, and a short-TTL (default 2h) role, scoped only to the specific resources the capability
declared for debugging — distinct from `resources:` which is production access.

## Why

During a Bedrock throttling incident on 2026-08-29, the on-call engineer couldn't tail
`/aws/lambda/essay-feedback-prod` because the spec hadn't listed the log group under
`resources:`. They requested a broader role from security; security correctly said no. The
engineer worked around it by paging a teammate with a wider role. The whole incident resolution
was delayed ~40 minutes.

The right fix is not to loosen production IAM. The right fix is to separate "production
runtime access" from "operator debugging access" at the spec layer:

- `resources:` remains minimal, long-TTL, no human can assume it directly.
- `debug_resources:` is new, 2h TTL, human-assumable via the JIT broker with on-call attestation,
  scoped to only what's listed.

This encodes the principle that **spec-driven means you solve problems in the spec, not around
it**.

## What this proposal does NOT do

- Does not change `resources:` semantics. Prod access is unchanged.
- Does not grant any default debug access. A capability must opt in with a `debug_resources:`
  block.
- Does not grant write access ever. Debug roles are read-only by policy.
- Does not bypass audit. Every JIT vend of a debug role is logged to the audit stream with the
  on-call attestation payload.

## Backward compatibility

Non-breaking. New field is optional. Capabilities without it have no human-assumable role.
