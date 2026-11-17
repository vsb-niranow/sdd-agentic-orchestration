package niranow.model_pinning

# Ensures model ARNs are version-pinned. Bedrock foundation-model ARNs end with a
# version suffix (e.g. `anthropic.claude-sonnet-4-6-20260815-v1:0`). Aliases like
# `:latest` or missing version suffixes are rejected.

default allow := false
allow if { count(deny) == 0 }

# -----------------------------------------------------------------------------
# Foundation-model ARN format
# -----------------------------------------------------------------------------

bedrock_foundation_model_re := `^arn:aws:bedrock:[a-z0-9-]+::foundation-model/[a-z0-9.-]+-v\d+:\d+$`

deny contains msg if {
    arn := input.spec.resources.model.arn
    arn != null
    not regex.match(bedrock_foundation_model_re, arn)
    msg := sprintf(
        "model_pinning.not_pinned: model ARN '%s' must match pattern '%s' (version-pinned foundation model)",
        [arn, bedrock_foundation_model_re]
    )
}

deny contains msg if {
    arn := input.spec.resources.model.arn
    contains(arn, ":latest")
    msg := "model_pinning.alias_forbidden: ':latest' alias is not permitted; pin a specific version"
}

# -----------------------------------------------------------------------------
# Inference profile backing must match
# -----------------------------------------------------------------------------
# OPA cannot resolve AWS API calls; this rule relies on the data bundle, which is
# refreshed daily by `tools/jit-iam-broker/refresh_inference_profile_bundle.py`.

deny contains msg if {
    profile_arn := input.spec.resources.model.inference_profile_arn
    profile_arn != null
    actual := input.data_bundle.inference_profiles[profile_arn].backing_model_arn
    declared := input.spec.resources.model.arn
    actual != declared
    msg := sprintf(
        "model_pinning.inference_profile_drift: profile '%s' backs model '%s' but spec declares '%s'",
        [profile_arn, actual, declared]
    )
}

# -----------------------------------------------------------------------------
# Temperature + max_tokens must be declared when model is declared
# -----------------------------------------------------------------------------

deny contains msg if {
    input.spec.resources.model.arn
    not input.spec.resources.model.temperature
    msg := "model_pinning.temperature_missing: temperature is required when model is declared"
}

deny contains msg if {
    input.spec.resources.model.arn
    not input.spec.resources.model.max_output_tokens
    msg := "model_pinning.max_output_tokens_missing: max_output_tokens is required when model is declared"
}

deny contains msg if {
    t := input.spec.resources.model.temperature
    t != null
    not is_number(t)
    msg := "model_pinning.temperature_type: temperature must be a number"
}

deny contains msg if {
    t := input.spec.resources.model.temperature
    is_number(t)
    not (t >= 0.0)
    msg := "model_pinning.temperature_range: temperature must be in [0.0, 1.0]"
}

deny contains msg if {
    t := input.spec.resources.model.temperature
    is_number(t)
    t > 1.0
    msg := "model_pinning.temperature_range: temperature must be in [0.0, 1.0]"
}
