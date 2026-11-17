"""
model_arn_pinned — local mirror of `policy/opa/model_pinning.rego`. The spec's
`resources.model.arn` must match the Bedrock foundation-model ARN pattern
with a pinned version. No `:latest`, no aliases, no bare IDs.
"""

from __future__ import annotations

import pathlib
import re

import yaml

BEDROCK_MODEL_RE = re.compile(
    r"^arn:aws:bedrock:[a-z0-9-]+::foundation-model/[a-z0-9.-]+-v\d+:\d+$"
)


def _extract_resources(spec_path: pathlib.Path) -> dict | None:
    body = spec_path.read_text(encoding="utf-8")
    try:
        _, _, rest = body.split("---", 2)
    except ValueError:
        return None
    lines = rest.splitlines()
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
        model = (parsed.get("resources") or {}).get("model")
        if not model:
            continue
        arn = model.get("arn")
        if arn is None:
            continue
        if not BEDROCK_MODEL_RE.match(arn):
            findings.append(Finding(
                rule_id="model_arn_pinned",
                severity="error",
                path=str(spec_path.relative_to(ctx.repo_root)),
                line=None,
                message=(
                    f"capability '{cap}' model ARN '{arn}' is not version-pinned. "
                    "Use arn:aws:bedrock:<region>::foundation-model/<model>-v<N>:<rev>."
                ),
            ))
        if ":latest" in arn:
            findings.append(Finding(
                rule_id="model_arn_pinned",
                severity="error",
                path=str(spec_path.relative_to(ctx.repo_root)),
                line=None,
                message=":latest alias detected; pin an explicit version.",
            ))
    return findings
