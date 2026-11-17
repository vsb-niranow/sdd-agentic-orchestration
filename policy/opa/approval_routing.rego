package niranow.approval_routing

# Decides which reviewer groups a merged proposal needs before it's considered approved.
# Routing reads the proposal frontmatter's `breaking:` flag and the touched capability's
# pii_class, then returns the set of required reviewer teams.

default required_reviewers := []

required_reviewers := reviewers if {
    reviewers := union({
        base_reviewers,
        breaking_reviewers,
        privacy_reviewers,
        schema_reviewers
    })
}

# -----------------------------------------------------------------------------
# Baseline: capability owners always required
# -----------------------------------------------------------------------------

base_reviewers := {owner |
    some owner in input.spec.frontmatter.owners
}

# -----------------------------------------------------------------------------
# Breaking changes: platform team
# -----------------------------------------------------------------------------

breaking_reviewers := {"@niranow/platform"} if {
    input.proposal.frontmatter.breaking == true
}
breaking_reviewers := set() if {
    input.proposal.frontmatter.breaking != true
}

# -----------------------------------------------------------------------------
# PII-touching: privacy team
# -----------------------------------------------------------------------------

privacy_reviewers := {"@niranow/privacy"} if {
    input.spec.frontmatter.pii_class >= 1
}
privacy_reviewers := set() if {
    not input.spec.frontmatter.pii_class
}
privacy_reviewers := set() if {
    input.spec.frontmatter.pii_class < 1
}

# -----------------------------------------------------------------------------
# Spec-schema changes: full platform + privacy + security
# -----------------------------------------------------------------------------

schema_reviewers := {"@niranow/platform", "@niranow/privacy", "@niranow/security"} if {
    input.spec.frontmatter.capability == "spec-schema"
}
schema_reviewers := set() if {
    input.spec.frontmatter.capability != "spec-schema"
}

# -----------------------------------------------------------------------------
# Deny if `breaking:` doesn't match the actual delta shape
# -----------------------------------------------------------------------------

deny contains msg if {
    input.proposal.frontmatter.breaking == false
    some kind
    kind == "REMOVED"
    some removed in input.delta[kind]
    startswith(removed.id, "SR-")
    msg := sprintf(
        "approval_routing.breaking_flag_wrong: delta removes SHALL requirement '%s' but proposal declares breaking: false",
        [removed.id]
    )
}

deny contains msg if {
    input.proposal.frontmatter.breaking == false
    some removed in input.delta.REMOVED
    regex.match(`^[A-Z]{2,3}-SR-\d{3}$`, removed.id)
    msg := sprintf(
        "approval_routing.breaking_flag_wrong: delta removes SHALL requirement '%s' but proposal declares breaking: false",
        [removed.id]
    )
}
