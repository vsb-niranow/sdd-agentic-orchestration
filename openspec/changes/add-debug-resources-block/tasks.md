# Tasks — add-debug-resources-block

## 1. Schema change
- [ ] Amend `openspec/specs/spec-schema/spec.md`
  - Add SS-SR-011: optional `debug_resources:` block
  - Define allowed resource types: cloudwatch_log_groups, xray_traces, bedrock_invocation_logs
  - Constrain TTL to ≤ 2h, min 30m

## 2. JIT broker change
- [ ] Extend `tools/jit-iam-broker/broker.py`
  - Recognize `debug_resources:` block
  - Require `--mode debug` to vend
  - Require `--oncall-attestation` argument signed with on-call rotation key
  - Emit audit record to `s3://niranow-security-audit/jit/debug/`
- [ ] Add trust policy variant `trust_policy_debug.json`
  - Only trust the JIT broker role
  - Require session tag `debug_proposal_id`

## 3. OPA policy
- [ ] Author `policy/opa/debug_resources.rego`
  - Enforce TTL bounds
  - Enforce read-only action set

## 4. Essay-feedback opt-in
- [ ] Open a follow-up proposal `add-essay-feedback-debug-resources` that opts the capability in
  - No changes here; separate proposal. One proposal per capability.
