package niranow.debug_resources

# Enforces SS-SR-011: optional `debug_resources:` block constraints.
# Introduced after the 2026-08 incident where on-call couldn't tail CloudWatch logs
# during a Bedrock throttling event. See docs/postmortems/2026-09-jit-too-narrow.md.

default allow := false
allow if { count(deny) == 0 }

allowed_resource_types := {
    "cloudwatch_log_groups",
    "xray_traces",
    "bedrock_invocation_logs"
}

# Any action that mutates state is forbidden in debug_resources.
write_action_prefixes := {
    "s3:Put", "s3:Delete",
    "dynamodb:Put", "dynamodb:Update", "dynamodb:Delete",
    "logs:Put",
    "bedrock:Invoke",
    "kms:Encrypt", "kms:Decrypt"
}

# -----------------------------------------------------------------------------
# TTL bounds: >= 30m, <= 2h
# -----------------------------------------------------------------------------

deny contains msg if {
    db := input.spec.debug_resources
    db
    ttl := db.ttl
    ttl != null
    not ttl in {"30m", "1h", "1h30m", "2h"}
    msg := sprintf(
        "debug_resources.ttl_invalid: '%s' is not an allowed TTL; use one of {30m, 1h, 1h30m, 2h}",
        [ttl]
    )
}

deny contains msg if {
    db := input.spec.debug_resources
    db
    not db.ttl
    msg := "debug_resources.ttl_missing: debug_resources.ttl is required"
}

# -----------------------------------------------------------------------------
# Resource-type allow-list
# -----------------------------------------------------------------------------

deny contains msg if {
    db := input.spec.debug_resources
    db
    some key
    db[key]
    key != "ttl"
    key != "requires_oncall_attestation"
    not key in allowed_resource_types
    msg := sprintf(
        "debug_resources.unknown_resource_type: '%s' not in %v",
        [key, allowed_resource_types]
    )
}

# -----------------------------------------------------------------------------
# No write actions ever
# -----------------------------------------------------------------------------

deny contains msg if {
    db := input.spec.debug_resources
    db
    some action in db.actions
    some prefix in write_action_prefixes
    startswith(action, prefix)
    msg := sprintf(
        "debug_resources.write_action_forbidden: action '%s' is a write; debug_resources is read-only by policy",
        [action]
    )
}

# -----------------------------------------------------------------------------
# No overlap with production resources
# -----------------------------------------------------------------------------

deny contains msg if {
    db_arn := db_arns_of(input.spec.debug_resources)
    prod_arn := prod_arns_of(input.spec.resources)
    some arn in db_arn
    arn in prod_arn
    msg := sprintf(
        "debug_resources.prod_overlap: ARN '%s' appears in both resources: and debug_resources:; debug must be a separate declaration",
        [arn]
    )
}

db_arns_of(db) := arns if {
    arns := union({
        {a | a := db.cloudwatch_log_groups[_]},
        {a | a := db.xray_traces[_]},
        {a | a := db.bedrock_invocation_logs[_]}
    })
}

prod_arns_of(r) := arns if {
    arns := union({
        {r.storage.submissions_bucket},
        {r.storage.feedback_table},
        {r.observability.log_group}
    })
}
