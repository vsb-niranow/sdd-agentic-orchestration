package niranow.pii_retention

# Enforces that retention is declared as an enum value, not prose.
# Enforces that PII-class >= 2 caps specify retention explicitly (no inherited default).

default allow := false
allow if { count(deny) == 0 }

allowed_retentions := {"none", "30d", "90d", "district_configured"}

deny contains msg if {
    r := input.spec.frontmatter.retention
    not r in allowed_retentions
    msg := sprintf(
        "pii_retention.enum_required: retention '%s' must be one of %v",
        [r, allowed_retentions]
    )
}

deny contains msg if {
    input.spec.frontmatter.retention == "district_configured"
    not input.spec.resources.tenant_config_ref
    msg := "pii_retention.tenant_config_ref_missing: retention 'district_configured' requires resources.tenant_config_ref"
}

deny contains msg if {
    pii := input.spec.frontmatter.pii_class
    pii >= 2
    input.spec.frontmatter.retention == "none"
    msg := sprintf(
        "pii_retention.pii_class_mismatch: pii_class=%d is incompatible with retention 'none' (would persist nothing of PII); use at least 30d",
        [pii]
    )
}
