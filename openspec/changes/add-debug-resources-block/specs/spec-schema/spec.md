## ADDED Requirements

### Requirement: SS-SR-011 — Optional `debug_resources:` block

A capability spec MAY declare a `debug_resources:` block distinct from `resources:`. If present,
the block SHALL validate against the schema at `policy/opa/schemas/debug_resources.schema.json`
and SHALL satisfy the following constraints:

- `ttl` is required, maximum 2h, minimum 30m
- `resources_allowed_types ⊆ {cloudwatch_log_groups, xray_traces, bedrock_invocation_logs}`
- No write actions permitted on any listed resource
- No overlap of ARN with the capability's `resources:` block (debug is a separate declaration,
  not a mirror)

#### Scenario: Debug block with 4h TTL
- **Given** `debug_resources.ttl: 4h`
- **Then** OPA SHALL reject with `debug_resources.ttl_exceeds_max`.

#### Scenario: Debug block attempting s3:PutObject
- **Given** a debug resource with action `s3:PutObject`
- **Then** OPA SHALL reject with `debug_resources.write_action_forbidden`.

#### Scenario: Valid debug block for essay-feedback
- **Given** `debug_resources: { ttl: 2h, cloudwatch_log_groups: ["/aws/lambda/essay-feedback-prod"] }`
- **Then** OPA SHALL allow
- **And** the JIT broker SHALL vend a role on request only if the `--oncall-attestation`
  argument is a valid signed token from the on-call rotation API.
