package niranow.spec_validation

# input: {
#   "spec": <parsed capability spec>,
#   "proposal": <parsed proposal frontmatter>,
#   "data_bundle": {
#     "retired_shall_ids": [...],
#     "eval_sets": {...},
#     "grace_until": {...},
#     "ownership": {...}
#   }
# }

default allow := false

allow if {
    count(deny) == 0
}

# -----------------------------------------------------------------------------
# Required frontmatter fields
# -----------------------------------------------------------------------------

required_fields := {
    "capability", "version", "breaking", "owners",
    "pii_class", "retention", "status"
}

deny contains msg if {
    some field in required_fields
    not input.spec.frontmatter[field]
    msg := sprintf("spec_validation.required_frontmatter: missing field '%s'", [field])
}

deny contains msg if {
    input.spec.frontmatter.pii_class
    not is_integer_in(input.spec.frontmatter.pii_class, 0, 3)
    msg := sprintf("spec_validation.pii_class_enum: pii_class must be integer in [0,3], got %v",
                   [input.spec.frontmatter.pii_class])
}

is_integer_in(v, lo, hi) if {
    v == floor(v)
    v >= lo
    v <= hi
}

# -----------------------------------------------------------------------------
# SHALL IDs are well-formed and never reused
# -----------------------------------------------------------------------------

deny contains msg if {
    some req in input.spec.requirements
    not regex.match(`^[A-Z]{2,3}-(SR|GR|NR|PR|AR)-\d{3}$`, req.id)
    msg := sprintf("spec_validation.shall_id_format: '%s' does not match required pattern", [req.id])
}

deny contains msg if {
    some req in input.spec.requirements
    req.id in input.data_bundle.retired_shall_ids
    msg := sprintf("spec_validation.shall_id_reuse: '%s' was retired in commit %s and cannot be reused",
                   [req.id, input.data_bundle.retired_shall_ids[req.id].commit])
}

# -----------------------------------------------------------------------------
# Every requirement has >= 1 scenario
# -----------------------------------------------------------------------------

deny contains msg if {
    some req in input.spec.requirements
    count(req.scenarios) == 0
    msg := sprintf("spec_validation.scenario_missing: requirement '%s' has no `#### Scenario:` block",
                   [req.id])
}

# -----------------------------------------------------------------------------
# Non-goals section exists and is non-empty
# -----------------------------------------------------------------------------

deny contains msg if {
    not input.spec.non_goals
    msg := "spec_validation.non_goals_missing: ## Non-Goals section is required"
}

deny contains msg if {
    input.spec.non_goals
    count(input.spec.non_goals) == 0
    msg := "spec_validation.non_goals_missing: ## Non-Goals section must contain at least one bullet"
}

# -----------------------------------------------------------------------------
# Eval contract: threshold required for model-invoking capabilities
# -----------------------------------------------------------------------------

deny contains msg if {
    input.spec.resources.model
    input.spec.resources.model.arn
    not input.spec.eval.threshold
    msg := "spec_validation.eval_threshold_missing: capabilities invoking a model must declare eval.threshold"
}

# -----------------------------------------------------------------------------
# Delta shape (for change proposals)
# -----------------------------------------------------------------------------

deny contains msg if {
    input.spec.is_delta
    input.spec.has_purpose_section
    msg := "spec_validation.delta_shape: delta file must not contain a top-level ## Purpose; only ADDED/MODIFIED/REMOVED sections"
}
