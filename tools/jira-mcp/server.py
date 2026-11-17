"""
Jira-MCP server.

Reads a merged OpenSpec change (`openspec/changes/<change-id>/`), parses
`tasks.md`, and creates:

- one Jira **Epic** per change proposal
- one Jira **Story** per top-level `- [ ]` checkbox in `tasks.md`

Every created ticket has:

- custom field `openspec_proposal_id` → `<change-id>`
- custom field `openspec_capability`   → `<spec.frontmatter.capability>`
- custom field `openspec_shall_ids`    → `[EF-SR-003, EF-SR-004, ...]` (parsed from
  `(EF-SR-003)` references in the task body)
- label `openspec`
- description linked to the proposal.md anchor

This is the audit anchor for the whole pipeline. Every production code change
traces back here.

The server is exposed as an MCP tool with three operations:

    openspec_create_tickets     — called by the merge webhook
    openspec_block_story        — called by OPA on policy failure
    openspec_update_story       — called by the AI reviewer

Dry-run mode (`--dry-run`) prints the ticket JSON instead of calling Jira.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import pathlib
import re
import sys
from typing import Iterable

import yaml

log = logging.getLogger("jira-mcp")

# --- Parsing -----------------------------------------------------------------

CHECKBOX_RE = re.compile(r"^- \[ \] (?P<title>.+)$")
SHALL_REF_RE = re.compile(r"\(([A-Z]{2,3}-(?:SR|GR|NR|PR|AR)-\d{3})\)")
SECTION_RE = re.compile(r"^## \d+\. (?P<title>.+)$")


@dataclasses.dataclass
class Story:
    title: str
    section: str                 # "1. Handler scaffold"
    description: str             # sub-bullets collapsed into markdown
    shall_ids: list[str]


@dataclasses.dataclass
class ProposalFrontmatter:
    change_id: str
    capability: str
    author: str
    reviewers: list[str]
    breaking: bool

    @classmethod
    def from_file(cls, path: pathlib.Path) -> "ProposalFrontmatter":
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValueError(f"{path}: missing frontmatter")
        _, frontmatter, _ = text.split("---", 2)
        data = yaml.safe_load(frontmatter)
        return cls(
            change_id=data["change_id"],
            capability=data["capability"],
            author=data["author"],
            reviewers=data.get("reviewers", []),
            breaking=bool(data.get("breaking", False)),
        )


def parse_tasks(path: pathlib.Path) -> Iterable[Story]:
    section = "unsectioned"
    pending_title: str | None = None
    pending_body: list[str] = []
    pending_shalls: set[str] = set()

    def flush():
        nonlocal pending_title, pending_body, pending_shalls
        if pending_title is not None:
            yield_story = Story(
                title=pending_title,
                section=section,
                description="\n".join(pending_body).rstrip(),
                shall_ids=sorted(pending_shalls),
            )
            pending_title = None
            pending_body = []
            pending_shalls = set()
            return yield_story
        return None

    stories: list[Story] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        m_sec = SECTION_RE.match(raw)
        if m_sec:
            # flush the previous story before entering a new section
            s = flush()
            if s:
                stories.append(s)
            section = m_sec.group("title")
            continue

        m_box = CHECKBOX_RE.match(raw)
        if m_box:
            # flush the previous task
            s = flush()
            if s:
                stories.append(s)
            pending_title = m_box.group("title").strip()
            pending_shalls.update(SHALL_REF_RE.findall(pending_title))
            continue

        if pending_title is not None:
            pending_body.append(raw)
            pending_shalls.update(SHALL_REF_RE.findall(raw))

    # flush the last one
    s = flush()
    if s:
        stories.append(s)
    return stories


# --- Jira payload construction ----------------------------------------------


def epic_payload(frontmatter: ProposalFrontmatter, proposal_path: pathlib.Path) -> dict:
    return {
        "fields": {
            "project": {"key": _project_for_capability(frontmatter.capability)},
            "issuetype": {"name": "Epic"},
            "summary": f"[{frontmatter.change_id}] {frontmatter.capability}",
            "description": _render_description(frontmatter, proposal_path),
            "labels": ["openspec", "openspec-epic"],
            "customfield_openspec_proposal_id": frontmatter.change_id,
            "customfield_openspec_capability": frontmatter.capability,
            "customfield_openspec_breaking": frontmatter.breaking,
        }
    }


def story_payload(frontmatter: ProposalFrontmatter, epic_key: str, story: Story) -> dict:
    return {
        "fields": {
            "project": {"key": _project_for_capability(frontmatter.capability)},
            "issuetype": {"name": "Story"},
            "summary": f"[{frontmatter.change_id} §{story.section}] {story.title}",
            "description": story.description or "_No further detail._",
            "labels": ["openspec"],
            "customfield_openspec_proposal_id": frontmatter.change_id,
            "customfield_openspec_capability": frontmatter.capability,
            "customfield_openspec_shall_ids": story.shall_ids,
            "customfield_openspec_section": story.section,
            "customfield_epic_link": epic_key,
        }
    }


def _project_for_capability(cap: str) -> str:
    # In production this is read from a Jira mapping config. For the lab, map
    # every capability to the project `AIWFB` (AI Writing Feedback).
    return os.environ.get("JIRA_PROJECT_KEY", "AIWFB")


def _render_description(fm: ProposalFrontmatter, proposal_path: pathlib.Path) -> str:
    rel = proposal_path.relative_to(proposal_path.parents[3])
    return (
        f"OpenSpec proposal: `{rel}`\n\n"
        f"Capability: `{fm.capability}`  |  Breaking: `{fm.breaking}`\n"
        f"Author: {fm.author}  |  Reviewers: {', '.join(fm.reviewers)}\n\n"
        f"> Linked SHALL IDs are stamped on each child story under custom "
        f"`openspec_shall_ids`."
    )


# --- OPA integration --------------------------------------------------------


def block_story(story_key: str, opa_rule: str, failing_message: str) -> dict:
    """Block a Jira story in response to an OPA policy failure.

    Called by the OPA gate's webhook when a merged proposal's stories need to
    be auto-blocked. The transition name is environment-specific; configure
    via `JIRA_TRANSITION_BLOCKED`.
    """
    return {
        "transition": {"id": os.environ.get("JIRA_TRANSITION_BLOCKED", "41")},
        "update": {
            "comment": [
                {
                    "add": {
                        "body": (
                            f"**OPA policy failure** — rule `{opa_rule}`\n\n"
                            f"{failing_message}\n\n"
                            f"This story is auto-blocked until the proposal is amended."
                        )
                    }
                }
            ]
        },
        "fields": {
            "customfield_opa_rule_failed": opa_rule,
        },
    }


# --- CLI entry point --------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--change", required=True, help="Change ID, e.g. add-essay-feedback-v1")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads instead of calling Jira")
    parser.add_argument("--repo-root", default=".", help="Path to the repo root")
    args = parser.parse_args(argv)

    repo_root = pathlib.Path(args.repo_root).resolve()
    change_dir = repo_root / "openspec" / "changes" / args.change
    if not change_dir.is_dir():
        print(f"error: {change_dir} does not exist", file=sys.stderr)
        return 2

    proposal_path = change_dir / "proposal.md"
    tasks_path = change_dir / "tasks.md"

    fm = ProposalFrontmatter.from_file(proposal_path)
    stories = list(parse_tasks(tasks_path))

    epic = epic_payload(fm, proposal_path)
    story_payloads = [story_payload(fm, epic_key="<epic-key>", story=s) for s in stories]

    if args.dry_run:
        out = {
            "epic": epic,
            "stories": story_payloads,
            "story_count": len(story_payloads),
        }
        print(json.dumps(out, indent=2, default=str))
        return 0

    # Production path would call Jira REST API here. Deliberately omitted
    # from the lab implementation; see README for the operational contract.
    print("error: live Jira calls not implemented in this lab fork; use --dry-run", file=sys.stderr)
    return 3


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    raise SystemExit(main())
