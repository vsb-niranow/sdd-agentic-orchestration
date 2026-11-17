"""
prompt_registry_coherent — the SHA-256 of every `prompts/<id>_v<N>.md` file
must match the hash recorded in `prompts/registry.yaml`. Mismatch is an
error.

See the 2026-08-10 prompt-drift incident in
`docs/postmortems/2026-08-prompt-drift-hotfix.md`.
"""

from __future__ import annotations

import hashlib
import pathlib

import yaml


def check(ctx) -> list:
    from runner import Finding  # type: ignore

    if not ctx.prompt_registry_path.exists():
        return [Finding(
            rule_id="prompt_registry_coherent",
            severity="error",
            path=str(ctx.prompt_registry_path.relative_to(ctx.repo_root)),
            line=None,
            message="prompts/registry.yaml is missing",
        )]

    registry = yaml.safe_load(ctx.prompt_registry_path.read_text(encoding="utf-8"))
    findings: list[Finding] = []

    for prompt_id, meta in registry.items():
        for entry in meta["versions"]:
            v = entry["v"]
            expected = entry["sha256"]
            file_path = ctx.prompts_dir / f"{prompt_id}_v{v}.md"
            if not file_path.exists():
                findings.append(Finding(
                    rule_id="prompt_registry_coherent",
                    severity="error",
                    path=str(ctx.prompt_registry_path.relative_to(ctx.repo_root)),
                    line=None,
                    message=f"registry references {prompt_id}@v{v} but {file_path} is missing",
                ))
                continue
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if actual != expected:
                findings.append(Finding(
                    rule_id="prompt_registry_coherent",
                    severity="error",
                    path=str(file_path.relative_to(ctx.repo_root)),
                    line=None,
                    message=(
                        f"hash mismatch for {prompt_id}@v{v} "
                        f"(expected {expected[:12]}…, got {actual[:12]}…). "
                        "Prompt text changed without a registry update — "
                        "see tighten-prompt-spec-coupling proposal."
                    ),
                ))

    return findings
