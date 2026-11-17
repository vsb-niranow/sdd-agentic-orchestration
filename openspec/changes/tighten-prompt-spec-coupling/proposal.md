---
change_id: tighten-prompt-spec-coupling
capability: multi
author: "@b-v-srujana"
reviewers:
  - "@niranow/platform"
  - "@niranow/applied-ai"
proposal_date: 2026-08-14
status: merged
merge_date: 2026-08-18
breaking: false
postmortem_ref: docs/postmortems/2026-08-prompt-drift-hotfix.md
---

## Summary

Make prompt files and their capability specs atomic: any change under `prompts/` requires a spec
delta in the same commit. CI fails otherwise. The prompt registry becomes the join between a
prompt file's content hash and the spec's declared `prompt_id@version`; mismatch is a build-stop.

## Why

During a Bedrock latency spike on 2026-08-10, a well-meaning engineer shortened
`prompts/essay_feedback_v7.md` to reduce input tokens. They didn't bump the version. They didn't
update the spec. The AI reviewer then flagged "un-specced prompt behavior" on the next
unrelated PR because the registry's recorded hash no longer matched the file. Nobody could
figure out why for ~90 minutes until the hotfix commit was git-blamed.

The root cause: prompt changes are a species of spec change. Treating them as code was the bug.

## What this proposal does

1. Add `tools/spec-lint/rules/prompt_registry_coherent.py`: content hash in
   `prompts/registry.yaml` must match the file's current SHA-256. Lint fails otherwise.
2. Add GitHub Actions workflow `prompt-delta-coupling.yaml`: any PR changing a file under
   `prompts/` MUST also change `openspec/changes/<id>/specs/<cap>/spec.md` for the owning
   capability. Workflow computes ownership via `prompts/registry.yaml`.
3. Add OPA rule `prompt_versioning.rego`: capability spec referencing `prompt_id@vN` must match
   the registry's `latest` version for that `prompt_id` at merge time.
4. Teach the AI reviewer to look at prompt content hash vs. spec-declared version first, before
   trying to analyze semantic drift. Content hash mismatch → short-circuit with specific error.

## What this proposal does NOT do

- Does not forbid prompt edits. It forbids prompt edits that aren't accompanied by a spec delta.
- Does not force a full re-run of all evals on every character change. Prompt change kicks off
  the owning capability's eval set only.

## Backward compatibility

Non-breaking. Existing prompt files are fine as long as their registry hash is current. The CI
rule only trips on new changes.
