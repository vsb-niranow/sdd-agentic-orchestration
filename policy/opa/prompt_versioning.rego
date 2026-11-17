package niranow.prompt_versioning

# Enforces SS-SR-012 at OPA merge time: capability's declared prompt_id@vN matches
# the registry's latest version. Detects stale references.

default allow := false
allow if { count(deny) == 0 }

deny contains msg if {
    some p in input.spec.resources.prompts
    parts := split(p.id, "@v")
    count(parts) == 2
    prompt_id := parts[0]
    declared_version := to_number(parts[1])
    latest := input.data_bundle.prompt_registry[prompt_id].latest
    declared_version < latest
    msg := sprintf(
        "prompt_versioning.stale: capability '%s' references '%s' but registry latest is v%d",
        [input.spec.frontmatter.capability, p.id, latest]
    )
}

deny contains msg if {
    some p in input.spec.resources.prompts
    parts := split(p.id, "@v")
    count(parts) != 2
    msg := sprintf(
        "prompt_versioning.id_format: '%s' must be <prompt_id>@v<integer>",
        [p.id]
    )
}

deny contains msg if {
    some p in input.spec.resources.prompts
    parts := split(p.id, "@v")
    count(parts) == 2
    prompt_id := parts[0]
    not input.data_bundle.prompt_registry[prompt_id]
    msg := sprintf(
        "prompt_versioning.unknown_prompt_id: '%s' not in prompts/registry.yaml",
        [p.id]
    )
}
