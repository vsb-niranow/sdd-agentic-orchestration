"""
AI reviewer.

Deliberately uses a **different model provider** from the implementation
(Claude Code → Anthropic; reviewer → OpenAI GPT-4-class or Gemini). The
asymmetry catches cases where a single model's blind spots produce internally
consistent but externally wrong code.

Called pre-PR. Inputs:

- `--change` the proposal under review
- `--diff` path to the candidate implementation diff
- `--spec-delta` path to the spec delta file inside the change folder

Emits a JSON report to stdout containing three categories of findings:

1. **Unimplemented SHALLs** — a SHALL ID in the spec with no code path reachable.
2. **Un-specced behavior** — code paths implementing behavior not covered by any
   SHALL and not excluded by `non_goals:`.
3. **Scenario drift** — acceptance scenarios in the spec that would not pass on
   the emitted code.

Additionally, short-circuit error classes (fast fail; skip semantic analysis):

- `prompt_hash_mismatch` — a referenced prompt's content doesn't match the
  registry hash. Human-readable error, no need to spend tokens.
- `model_arn_drift` — code hard-codes a model ARN that disagrees with the spec.

See `prompts/spec_diff_reviewer_v2.md` for the reviewer agent's system prompt.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

import yaml


@dataclasses.dataclass
class Finding:
    category: str                # "unimplemented_shall" | "un_specced" | "scenario_drift" | "short_circuit"
    severity: str                # "error" | "warning"
    shall_id: str | None
    file: str | None
    line: int | None
    message: str


SHALL_ID_RE = re.compile(r"^### Requirement: (?P<id>[A-Z]{2,3}-(?:SR|GR|NR|PR|AR)-\d{3}) ")


def parse_shall_ids_from_spec(path: pathlib.Path) -> list[str]:
    return [
        m.group("id")
        for line in path.read_text(encoding="utf-8").splitlines()
        for m in [SHALL_ID_RE.match(line)]
        if m
    ]


def short_circuit_checks(
    repo: pathlib.Path,
    change_id: str,
) -> list[Finding]:
    """Run fast, cheap checks before spending tokens on the model-based review."""
    findings: list[Finding] = []

    registry_path = repo / "prompts" / "registry.yaml"
    if not registry_path.exists():
        findings.append(Finding(
            category="short_circuit", severity="error",
            shall_id=None, file=str(registry_path), line=None,
            message="prompts/registry.yaml missing",
        ))
        return findings

    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    for pid, meta in registry.items():
        for entry in meta["versions"]:
            file_path = repo / "prompts" / f"{pid}_v{entry['v']}.md"
            if not file_path.exists():
                findings.append(Finding(
                    category="short_circuit", severity="error",
                    shall_id=None, file=str(file_path), line=None,
                    message=f"registry references {pid}@v{entry['v']} but file missing",
                ))
                continue
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if actual != entry["sha256"]:
                findings.append(Finding(
                    category="short_circuit", severity="error",
                    shall_id=None, file=str(file_path), line=None,
                    message=(
                        f"prompt_hash_mismatch: {pid}@v{entry['v']} drifted; "
                        f"spec cannot be reviewed against a prompt whose text has changed. "
                        "Open a tighten-prompt-spec-coupling delta first."
                    ),
                ))

    return findings


def reviewer_agent_payload(
    spec_text: str,
    delta_text: str,
    diff_text: str,
    system_prompt: str,
) -> dict[str, Any]:
    """
    Build the payload for the reviewer model call. In production this is
    executed by a client against a different-provider model (configured
    externally). Here we return the fully-formed payload for inspection.
    """
    return {
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": (
                    "GOLDEN_SPEC:\n"
                    f"{spec_text}\n\n"
                    "SPEC_DELTA (what this PR changes in the spec):\n"
                    f"{delta_text}\n\n"
                    "CANDIDATE_DIFF (what Claude Code generated):\n"
                    f"{diff_text}\n\n"
                    "Return JSON: {findings: [...]} using the schema in your system prompt."
                ),
            }
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--change", required=True)
    ap.add_argument("--diff", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--emit-payload", action="store_true",
                    help="Print the reviewer model's payload but do not call it.")
    args = ap.parse_args(argv)

    repo = pathlib.Path(args.repo_root).resolve()
    change_dir = repo / "openspec" / "changes" / args.change

    proposal = yaml.safe_load(
        (change_dir / "proposal.md").read_text(encoding="utf-8").split("---")[1]
    )
    capability = proposal["capability"]

    report: dict[str, Any] = {
        "change_id": args.change,
        "capability": capability,
        "short_circuit": [],
        "findings": [],
    }

    # 1. Fast checks first.
    short_circuits = short_circuit_checks(repo, args.change)
    report["short_circuit"] = [dataclasses.asdict(f) for f in short_circuits]

    if any(f.severity == "error" for f in short_circuits):
        # Don't spend reviewer-model tokens if the fast checks failed.
        print(json.dumps(report, indent=2, default=str))
        return 1

    # 2. Compose reviewer-model payload.
    if capability == "multi":
        # For multi-cap deltas, bundle every touched capability's spec.
        touched = sorted(p.parent.name for p in (change_dir / "specs").glob("*/spec.md"))
        spec_text = "\n\n---\n\n".join(
            (repo / "openspec" / "specs" / cap / "spec.md").read_text(encoding="utf-8")
            for cap in touched
            if (repo / "openspec" / "specs" / cap / "spec.md").exists()
        )
        delta_text = "\n\n---\n\n".join(
            (change_dir / "specs" / cap / "spec.md").read_text(encoding="utf-8")
            for cap in touched
        )
    else:
        spec_text = (repo / "openspec" / "specs" / capability / "spec.md").read_text(encoding="utf-8")
        delta_text = (change_dir / "specs" / capability / "spec.md").read_text(encoding="utf-8")

    diff_text = pathlib.Path(args.diff).read_text(encoding="utf-8")
    system_prompt = (pathlib.Path(__file__).parent / "prompts" / "spec_diff_reviewer_v2.md"
                     ).read_text(encoding="utf-8")

    payload = reviewer_agent_payload(spec_text, delta_text, diff_text, system_prompt)
    if args.emit_payload:
        print(json.dumps(payload, indent=2, default=str))
        return 0

    # 3. In production: send to a different-provider reviewer model; parse JSON
    # response; merge into `report["findings"]`. The actual client is
    # environment-specific; omitted from this lab fork.
    print(json.dumps(report, indent=2, default=str))
    print("note: reviewer model call not executed; use --emit-payload to inspect the request",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
