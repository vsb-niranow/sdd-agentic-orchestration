"""
shall_id_coverage — every SHALL ID in a golden capability spec must be
referenced by at least one test file name under `services/<cap>/tests/`.

Test naming convention (from CLAUDE.md):

    tests/test_<cap>_<shall_id>_<scenario_slug>.py

Example: `tests/test_essay_feedback_ef_sr_003_grade_band_filter.py`.
"""

from __future__ import annotations

import pathlib
import re
from typing import Iterable

SHALL_ID_RE = re.compile(r"^### Requirement: (?P<id>[A-Z]{2,3}-(?:SR|GR|NR|PR|AR)-\d{3}) ")


def _shall_ids_in_spec(spec_path: pathlib.Path) -> list[str]:
    return [
        m.group("id")
        for line in spec_path.read_text(encoding="utf-8").splitlines()
        for m in [SHALL_ID_RE.match(line)]
        if m
    ]


def check(ctx) -> list:
    from runner import Finding  # type: ignore

    findings: list[Finding] = []

    for cap, spec_path in ctx.specs.items():
        shall_ids = _shall_ids_in_spec(spec_path)
        if not shall_ids:
            continue

        tests_dir = ctx.source_tree / cap / "tests"
        if not tests_dir.is_dir():
            # Capabilities with no code (like `spec-schema`) are allowed; skip.
            if cap == "spec-schema":
                continue
            findings.append(Finding(
                rule_id="shall_id_coverage",
                severity="error",
                path=str(spec_path.relative_to(ctx.repo_root)),
                line=None,
                message=f"capability '{cap}' has SHALL IDs but no tests directory at {tests_dir}",
            ))
            continue

        test_filenames = "\n".join(p.name for p in tests_dir.rglob("test_*.py"))
        for shall_id in shall_ids:
            slug = shall_id.lower().replace("-", "_")
            if slug not in test_filenames:
                findings.append(Finding(
                    rule_id="shall_id_coverage",
                    severity="error",
                    path=str(spec_path.relative_to(ctx.repo_root)),
                    line=None,
                    message=(
                        f"SHALL ID '{shall_id}' is not referenced by any test under "
                        f"services/{cap}/tests/. Expected a filename containing '{slug}'."
                    ),
                ))

    return findings
