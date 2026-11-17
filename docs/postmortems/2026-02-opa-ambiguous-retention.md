# Postmortem — OPA rejecting valid proposals over ambiguous retention (2026-02-04 — 2026-02-11)

**Severity:** P4 (no production impact; developer friction + false confidence
in the gate)

**Affected capability:** `essay-feedback` and two others under development

**Spec delta that resolved it:** [implicit in the schema] — retention is an
enum. `SS-SR-005`.

## Summary

OPA rejected ~40% of early proposals over a single policy check: "every
PII-touching capability must declare a retention period." The retention field
was free-form prose. One early proposal said `retention: "retained per
district policy"` — human-readable, machine-useless. OPA rejected. Author
re-worded. OPA rejected. Author re-worded again. OPA rejected again.

By the fourth rejection cycle the author asked "what does OPA actually
want," which was when we realized OPA couldn't *want* anything specific
because the field wasn't an enum.

## Root cause

**Human:** Treated OPA as a style checker on prose. OPA cannot interpret
prose.

**Technical:** Schema declared `retention: string` with a description. Policy
tried to parse the string into one of a few canonical values via regex and
failed on most edge cases.

## What changed

1. **Schema:** retention is now an enum (`none | 30d | 90d |
   district_configured`). OPA rejects everything else.
2. **Lint:** mirrored the enum at pre-push.
3. **Documentation:** the project.md lists the enum values. Every spec
   author sees it.

## The lesson

If a human needs to interpret the spec, OPA can't. We moved every policy
check that had been swallowing ambiguity to an enum. False-rejection rate
dropped from ~40% to effectively zero.

This is the postmortem that produced the first of the "spec quality"
principles we now keep posted:

> **The spec is a contract with your tooling, not just your teammates.**
> Every downstream tool — Jira-MCP, OPA, JIT, lint, AI reviewer — is a
> consumer. Design the spec schema with those consumers in mind, or they'll
> each build their own shadow schema.
