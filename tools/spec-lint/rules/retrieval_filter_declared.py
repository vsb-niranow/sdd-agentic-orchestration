"""
retrieval_filter_declared — mirrors OPA's `retrieval_filter.rego` at the
local-dev layer. Fires pre-push so developers see the same error message
locally that OPA would raise at merge time.

Flags any capability spec whose `resources.retrieval.index` is set but
`resources.retrieval.retrieval_filter` is missing or null.
"""

from __future__ import annotations

import pathlib
import re

import yaml


def _extract_resources(spec_path: pathlib.Path) -> dict | None:
    body = spec_path.read_text(encoding="utf-8")
    try:
        _, _, rest = body.split("---", 2)
    except ValueError:
        return None

    lines = rest.splitlines()
    # find "## Resources" then the following ```yaml fence
    try:
        idx = next(i for i, l in enumerate(lines) if l.strip() == "## Resources")
    except StopIteration:
        return None

    fence_start = next(
        (j + 1 for j in range(idx + 1, len(lines)) if lines[j].strip().startswith("```yaml")),
        None,
    )
    if fence_start is None:
        return None

    fence_end = next(
        (k for k in range(fence_start, len(lines)) if lines[k].strip() == "```"),
        None,
    )
    if fence_end is None:
        return None

    return yaml.safe_load("\n".join(lines[fence_start:fence_end])) or {}


def check(ctx) -> list:
    from runner import Finding  # type: ignore

    findings: list[Finding] = []
    for cap, spec_path in ctx.specs.items():
        parsed = _extract_resources(spec_path)
        if not parsed:
            continue
        retrieval = (parsed.get("resources") or {}).get("retrieval")
        if not retrieval:
            continue
        if not retrieval.get("index"):
            continue
        if not retrieval.get("retrieval_filter"):
            findings.append(Finding(
                rule_id="retrieval_filter_declared",
                severity="error",
                path=str(spec_path.relative_to(ctx.repo_root)),
                line=None,
                message=(
                    f"capability '{cap}' declares a retrieval index but omits "
                    "resources.retrieval.retrieval_filter — SS-SR-006 requires it. "
                    "See docs/postmortems/2026-04-retrieval-filter-leak.md."
                ),
            ))
    return findings
