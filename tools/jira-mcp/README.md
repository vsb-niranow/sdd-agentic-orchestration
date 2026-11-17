# jira-mcp

MCP server that bridges merged OpenSpec proposals to Jira.

## What it does

1. On every merge to `main` under `openspec/changes/<id>/`, the GitHub Action
   `.github/workflows/opa-gate.yaml` invokes `server.py --change <id>`.
2. The server parses `proposal.md` frontmatter and `tasks.md`.
3. It creates one epic plus one story per top-level `- [ ]` checkbox, stamping
   the Jira custom field `openspec_proposal_id` with `<id>` and
   `openspec_shall_ids` with every `(XX-YY-NNN)` reference found in the task
   body.
4. On OPA policy failure (reported out of band via a webhook), the server
   transitions the affected stories to `Blocked` with the failing rule and
   message attached as a comment.

## Dry-run

```bash
python server.py --change add-essay-feedback-v1 --dry-run --repo-root ../..
```

Prints the full epic + story payloads as they would be sent to Jira. Useful
for verifying `tasks.md` parses cleanly before merging a proposal.

## MCP tool surface

When run as an MCP server (not CLI), the following tools are exposed:

| Tool | Purpose |
|------|---------|
| `openspec_create_tickets(change_id)` | Called by the merge webhook. Returns `{epic_key, story_keys[]}`. |
| `openspec_block_story(story_key, opa_rule, message)` | Called by the OPA gate. Transitions to Blocked. |
| `openspec_update_story(story_key, body)` | Called by the AI reviewer to append findings. |
| `openspec_link_pr(story_key, pr_url)` | Called by CI on PR open to cross-link. |

## Design notes

- **Deterministic ticket layout.** One checkbox = one story, always. Fine-
  grained task lists create too much Jira noise; coarse task lists hide
  SHALL coverage. We converged on "one story per implementation surface"
  (handler, retrieval, prompts, guardrails, IaC, evals, tests, obs).
- **SHALL IDs are the join.** Lint, tests, AI reviewer, and Jira all key off
  the SHALL ID. The custom field is indexed so you can filter Jira for
  "stories implementing EF-SR-003" and get a single reproducible list.
- **No retroactive editing of merged stories.** If a proposal is amended
  (rare), a new proposal gets a new epic. Jira's audit trail is sacred.
