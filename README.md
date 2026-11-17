# lab-agentic-sdd-orchestration

Reference implementation of a **spec-driven delivery (SDD) pipeline** for applied-AI features,
built around OpenSpec change proposals as the single entry point for Jira, IAM, code generation,
lint, and AI review.

The seed product was an **AI writing-feedback assistant for a 6–12 ELA platform** — rubric-aligned
essay feedback delivered to district customers. This repo preserves the pipeline, the spec schema,
the policy bundle, and the deltas that shaped it in production.

> **The thesis.** When a human writes the code, specs can be loose — judgment fills the gaps.
> When **Claude Code writes the code, every gap becomes production**. So the spec has to pin the
> model version, reference versioned prompt IDs instead of prompt text, declare retrieval filters
> and eval thresholds, and be machine-parseable by OPA and the JIT IAM broker. The Applied AI
> Engineer's highest-leverage artifact is no longer the prompt — it is the spec.

## Pipeline at a glance

```
  ┌──────────────────┐
  │ OpenSpec change  │  openspec/changes/<change-id>/{proposal,tasks,specs/…}
  │   proposal       │
  └────────┬─────────┘
           │ merge to main
           ▼
  ┌──────────────────┐   fail → auto-block Jira story
  │   OPA gate       │────────────────────────────────┐
  │ (policy-as-code) │                                │
  └────────┬─────────┘                                │
           │ pass                                     │
           ▼                                          ▼
  ┌──────────────────┐                      policy/opa/*.rego
  │ Jira-MCP server  │  creates epic + 1 story / task,
  │                  │  stamps proposal_id in custom field
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐   reads resources: block →
  │ JIT IAM broker   │   vends time-boxed AWS role (TTL ≤ 4h)
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐   given merged spec + task + IAM,
  │   Claude Code    │   generates Lambda, RAG retriever,
  │ (implementation) │   prompt binder, eval runner, IaC
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐   every SHALL ID → ≥1 test;
  │  Spec-aware lint │   every prompt call → versioned ID;
  │                  │   every model invoke → pinned ARN
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐   different-provider reviewer model
  │  AI reviewer     │   diffs code vs. spec delta; flags:
  │ (pre-PR)         │     • unimplemented SHALLs
  │                  │     • un-specced behavior
  │                  │     • scenario drift
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐   human reviews **against the spec**,
  │   Human PR       │   not from scratch
  └──────────────────┘
```

## What's in this repo

| Path | Purpose |
|------|---------|
| `openspec/project.md` | Project conventions. Loaded into every Claude Code / AI-reviewer context. |
| `openspec/specs/<cap>/spec.md` | Current "golden" state of each capability — what the system *is*. |
| `openspec/changes/<id>/` | Change proposals. Each contains `proposal.md`, `tasks.md`, and `specs/<cap>/spec.md` **deltas** (`## ADDED`, `## MODIFIED`, `## REMOVED`). |
| `policy/opa/*.rego` | OPA bundle. Gate on every merged proposal. |
| `tools/jira-mcp/` | MCP server that reads `tasks.md` and creates Jira epic + stories. |
| `tools/jit-iam-broker/` | Parses the spec's `resources:` block and vends a time-boxed AWS role. |
| `tools/spec-lint/` | Custom lint rules; keyed off SHALL IDs, prompt IDs, model ARNs. |
| `tools/ai-reviewer/` | Spec-vs-code reviewer agent. Runs pre-PR. |
| `prompts/` | Versioned prompt registry. Specs reference `prompt_id`, never prompt text. |
| `evals/<set>/` | Eval sets. Each has a `manifest.yaml` with threshold + isolation declaration. |
| `.github/workflows/` | CI wiring: OPA gate, spec lint, prompt-coupling guard, AI review. |
| `docs/postmortems/` | The incidents that drove each schema delta. |
| `docs/adr/` | Architectural decisions (OpenSpec-as-entry, prompt-id-not-text, two-model review). |

## The five rules a spec has to obey (so the pipeline can consume it)

1. **One capability per proposal, atomic deltas.** If a change touches two capabilities it becomes
   two proposals. Otherwise OPA can't reason about blast radius and JIT IAM can't scope the role.
2. **Every SHALL has an ID + at least one `#### Scenario:`.** The ID is the join key for lint,
   tests, Jira stories, and the AI reviewer. No ID, no traceability.
3. **Machine-readable `resources:` block.** AWS ARNs, model IDs, data classifications. Consumed by
   JIT IAM and OPA. Prose doesn't parse.
4. **Explicit `non_goals:`.** The AI reviewer uses this to flag un-specced behavior. Without it the
   reviewer either hallucinates violations or misses real scope creep.
5. **`breaking: true|false` at the top.** OPA routes breaking changes to platform-team approval
   and non-breaking changes (copy, prompt-param tuning, threshold bumps) through a lighter chain.

Full schema in `docs/spec-schema.md`. The meta-spec that defines this schema is itself
version-controlled at `openspec/specs/spec-schema/spec.md`.

## The deltas that shaped the schema

Each of these started as a production problem and ended as a spec-schema change. They are the
real reason this pipeline exists.

| Delta | Incident | Schema change |
|-------|----------|---------------|
| [`add-retrieval-filter-guardrail`](openspec/changes/add-retrieval-filter-guardrail/) | A 6th grader was shown an 11th-grade exemplar; output filter existed, retrieval filter did not. | Added required `retrieval_filter:` to every RAG capability. OPA rejects omission. |
| [`add-eval-isolation-policy`](openspec/changes/add-eval-isolation-policy/) | Few-shot vectors overlapped with the eval set; CI scores drifted from production. | Added `eval_isolation: strict` enum. OPA rejects any capability where retrieval index intersects an eval set. |
| [`tighten-prompt-spec-coupling`](openspec/changes/tighten-prompt-spec-coupling/) | A latency hotfix edited prompt text without bumping the version; AI reviewer then flagged unrelated PRs. | CI rule: any change under `prompts/` requires a spec delta in the same commit. |
| [`add-debug-resources-block`](openspec/changes/add-debug-resources-block/) | JIT role too narrow to tail Bedrock logs during an incident; dev wanted broader prod role. | Added `debug_resources:` block, 2h TTL, separate OPA policy. |

## What this repo is **not**

- Not the full essay-feedback product. The capability specs are real-shape; the Lambda code
  Claude Code would emit is not committed. Specs are the artifact.
- Not a general-purpose OpenSpec fork. This is the opinionated, applied-AI variant: spec fields
  cover models, prompts, retrieval, evals, and guardrails that a generic software spec wouldn't.
- Not a demo of agentic autonomy. The pipeline is deliberately humans-in-the-loop at the PR seam
  and at the OPA-fails-to-20% escalation.

## Running the pipeline locally

```bash
# 1. Validate a change proposal against the schema + OPA
make validate CHANGE=add-essay-feedback-v1

# 2. Dry-run Jira story creation from tasks.md
python tools/jira-mcp/server.py --dry-run --change add-essay-feedback-v1

# 3. Simulate JIT IAM scoping
python tools/jit-iam-broker/broker.py --change add-essay-feedback-v1 --ttl 2h --mode preview

# 4. Run spec-aware lint over the current tree
python tools/spec-lint/runner.py

# 5. Run AI reviewer against a candidate diff
python tools/ai-reviewer/reviewer.py --change add-essay-feedback-v1 --diff /tmp/claude-code-output.diff
```

## License

MIT. Reference material; adapt freely.
