"""
prompt_id_pinned — every string in source that looks like a prompt system
message must come from `prompts/registry.yaml`, not an inlined literal.

The rule is intentionally crude: it flags any Python/TS file containing a
string literal longer than 200 characters that also contains two or more of
the following substrings: `You are`, `Your task`, `You must`, `Respond with`,
`JSON`. We prefer false positives here — the fix is always to move the string
into `prompts/<id>_vN.md` and register it.
"""

from __future__ import annotations

import pathlib
import re

HEURISTIC_WORDS = ("You are", "Your task", "You must", "Respond with", "JSON")
LITERAL_RE = re.compile(r'("""|\'\'\'|"|\')(?P<body>.{200,}?)(\1)', re.DOTALL)


def check(ctx) -> list:
    from runner import Finding  # type: ignore

    findings: list[Finding] = []
    for path in ctx.source_tree.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for m in LITERAL_RE.finditer(text):
            body = m.group("body")
            hits = sum(1 for w in HEURISTIC_WORDS if w in body)
            if hits >= 2:
                line = text[:m.start()].count("\n") + 1
                findings.append(Finding(
                    rule_id="prompt_id_pinned",
                    severity="error",
                    path=str(path.relative_to(ctx.repo_root)),
                    line=line,
                    message=(
                        "Looks like an inline prompt literal "
                        f"(~{len(body)} chars). Move it into prompts/<id>_vN.md, "
                        "register the hash, and reference prompt_id@version in the spec."
                    ),
                ))
    return findings
