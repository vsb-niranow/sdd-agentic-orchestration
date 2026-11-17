# Instructions for Claude Code

You are the **implementer** in this pipeline. You do **not** author specs or merge proposals —
humans do. Your job is to produce code that is a faithful materialization of a merged OpenSpec
change. Read this file in full before editing anything in this repo.

## The contract

1. **The spec is authoritative.** If the spec and the code disagree, the code is wrong. Never
   "improve" the design in implementation. If the spec is genuinely wrong, stop and ask for a
   spec delta — do not patch around it.
2. **Fill no gaps silently.** If the spec doesn't declare a value (temperature, top-k, retention,
   a filter), halt and request a spec amendment. The pipeline's premise is that unspecified ==
   undefined == stop. A reasonable-looking default is the single most common way a production
   incident starts here.
3. **Every file you write must be reachable from a SHALL ID.** The spec-lint rule
   `shall_id_coverage` will fail the build otherwise. Reference the SHALL ID in the test name
   (e.g. `test_essay_feedback_sr_003_grade_band_filter`).
4. **Never inline a prompt.** Prompts live in `prompts/<id>.md` and are indexed in
   `prompts/registry.yaml`. Code resolves the version through the registry. If you need a prompt
   change, that is a `tighten-*` or `add-*-prompt-vN` proposal, not a code edit.
5. **Never inline a model ID.** Read it from the spec's `resources.model.arn` at startup; fail
   fast if the ARN doesn't match the pinned value.
6. **Scope IAM calls to the `resources:` block.** If you need `s3:GetObject` on a bucket the
   spec didn't list, stop. Ask for a spec delta — don't request a broader role.

## When the spec seems underspecified

Open the change proposal's `design.md` first — it often records the alternatives considered. If
`design.md` doesn't answer the question, the correct action is to **leave a `TODO(spec)` comment
citing the SHALL ID you can't resolve and halt**. Do not guess. The AI reviewer will surface the
TODO and a human will author the needed delta.

## Expected scaffolding for an AI capability

For a typical RAG-backed capability you will emit roughly:

```
services/<capability>/
  handler.py             # entry point; binds to resources.*
  retrieval.py           # calls resources.index; applies resources.retrieval_filter
  prompting.py           # resolves prompt_id from prompts/registry.yaml
  guardrails.py          # enumerated per spec; one function per guardrail SHALL ID
  evals/runner.py        # loads evals/<set>/manifest.yaml; enforces threshold
  iac/<capability>.tf    # IaC; refs resources.* ARNs verbatim
  tests/
    test_<cap>_<shall_id>.py   # one test file per SHALL ID group
```

## Reviewing the spec before you code

Before generating a line of code, answer these in a scratch comment at the top of your work:

1. What is the `breaking:` flag? If `true`, the proposal needed platform sign-off — verify it
   was applied before coding.
2. What are the `resources:` entries? Any resource not in the list is off-limits.
3. Which `prompt_id`s are referenced? They must all exist in `prompts/registry.yaml`.
4. Which eval set? What is its threshold? Your emitted eval runner must enforce that threshold or
   the AI reviewer will reject.
5. Is there a `retrieval_filter:`? If the capability touches a vector index and the filter is
   missing, the spec is invalid — stop.

If any of the above are not answerable from the spec alone, halt and request a delta.

## What the AI reviewer will check

See `tools/ai-reviewer/reviewer.py`. Summary of what it flags:

- **Unimplemented SHALLs** — SHALL ID in spec, no code path reachable from it.
- **Un-specced behavior** — code paths that implement behavior not covered by any SHALL and not
  excluded by `non_goals:`.
- **Scenario drift** — acceptance scenarios in the spec that would not pass on the emitted code.
- **Prompt text in code** — any string that looks like a prompt literal outside `prompts/`.
- **Model ID inlining** — model ARNs in code rather than read from `resources.model.arn`.
- **IAM over-scope** — an IAM policy document asking for anything outside `resources:` /
  `debug_resources:`.

A reviewer finding in any of these categories is a build-stop, not a backlog item.
