"""
Spec-aware lint runner.

Discovers rules under `tools/spec-lint/rules/`, loads every capability spec,
every delta spec, the prompt registry, and the current source tree, and runs
each rule against the combined view.

Each rule is a Python module exposing:

    def check(ctx: LintContext) -> list[Finding]: ...

Findings have `rule_id`, `severity`, `path`, `line`, and `message`. A finding
with `severity == "error"` fails the build.

Run:

    python tools/spec-lint/runner.py             # fail on error findings
    python tools/spec-lint/runner.py --changed   # only files in the current PR
    python tools/spec-lint/runner.py --rule shall_id_coverage
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import json
import pathlib
import sys
from typing import Iterable

RULES_DIR = pathlib.Path(__file__).parent / "rules"


@dataclasses.dataclass
class Finding:
    rule_id: str
    severity: str           # "error" | "warning" | "info"
    path: str
    line: int | None
    message: str


@dataclasses.dataclass
class LintContext:
    repo_root: pathlib.Path
    specs: dict[str, pathlib.Path]
    deltas: dict[str, list[pathlib.Path]]
    prompt_registry_path: pathlib.Path
    prompts_dir: pathlib.Path
    source_tree: pathlib.Path
    changed_only: bool
    changed_files: set[pathlib.Path] | None


def discover_rules() -> list[str]:
    return sorted(p.stem for p in RULES_DIR.glob("*.py") if not p.stem.startswith("_"))


def load_rule(rule_id: str):
    sys.path.insert(0, str(RULES_DIR))
    try:
        return importlib.import_module(rule_id)
    finally:
        sys.path.pop(0)


def build_context(repo_root: pathlib.Path, changed_only: bool) -> LintContext:
    specs = {
        p.parent.name: p
        for p in (repo_root / "openspec" / "specs").glob("*/spec.md")
    }
    deltas: dict[str, list[pathlib.Path]] = {}
    for p in (repo_root / "openspec" / "changes").glob("*/specs/*/spec.md"):
        deltas.setdefault(p.parent.name, []).append(p)

    return LintContext(
        repo_root=repo_root,
        specs=specs,
        deltas=deltas,
        prompt_registry_path=repo_root / "prompts" / "registry.yaml",
        prompts_dir=repo_root / "prompts",
        source_tree=repo_root / "services",
        changed_only=changed_only,
        changed_files=None,  # populated by the CI shim
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--rule", action="append", help="Only run the named rule; may repeat.")
    ap.add_argument("--changed", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    ctx = build_context(pathlib.Path(args.repo_root).resolve(), args.changed)
    rules = args.rule or discover_rules()

    all_findings: list[Finding] = []
    for rid in rules:
        mod = load_rule(rid)
        try:
            findings = mod.check(ctx)
        except Exception as exc:
            all_findings.append(Finding(
                rule_id=rid, severity="error", path="<rule>", line=None,
                message=f"rule crashed: {exc!r}"
            ))
            continue
        all_findings.extend(findings)

    if args.json:
        print(json.dumps([dataclasses.asdict(f) for f in all_findings], indent=2))
    else:
        for f in all_findings:
            loc = f"{f.path}:{f.line}" if f.line else f.path
            print(f"[{f.severity.upper()}] {f.rule_id} @ {loc}: {f.message}")

    return 1 if any(f.severity == "error" for f in all_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
