# jit-iam-broker

Vends short-TTL AWS roles scoped to the specific ARNs declared in a capability
spec's `resources:` (production) or `debug_resources:` (debugging) block.

## Why this exists

Specs-as-code only work if downstream tooling actually reads the spec. The JIT
broker is the enforcement point for "no standing access to production": every
role is minted on demand from the spec and expires. If an engineer needs an
AWS permission, they must add it to the spec — not request it ad-hoc.

## Commands

```bash
# Dry-run — print the policy document that would be vended for prod
python broker.py --change add-essay-feedback-v1 --mode preview

# Preview the debug role (requires an on-call attestation JWT)
python broker.py \
  --change add-essay-feedback-v1 \
  --mode debug \
  --oncall-attestation "$ONCALL_JWT" \
  --ttl 2h

# In production the GitHub Action invokes --mode prod on deploy.
```

## Guarantees

1. **ARNs only.** No wildcards. If the spec lists three bucket ARNs, the
   vended policy references exactly those three.
2. **TTL clamped.** `--ttl` is honored up to the spec's declared `resources.ttl`
   (production) or 2h (debug). Longer values are silently clamped and logged.
3. **Session tags stamped.** Every role carries `openspec_proposal_id`,
   `openspec_capability`, and (for debug) `oncall_attestation_id`. These
   session tags drive audit queries.
4. **Read-only in debug.** The `debug_resources:` block only accepts
   resource types in the `debug_resources.rego` allow-list, and the action
   templates for those types contain only read verbs. Defense in depth.
5. **No overlap with production.** OPA rejects specs whose
   `debug_resources` ARNs overlap `resources`; the broker double-checks and
   refuses to vend on overlap.

## Audit

Every vend emits a JSON record to CloudWatch (`NiraNow/JIT/Vends`) and an
S3 object under `s3://niranow-security-audit/jit/<mode>/<yyyymmdd>/<change-id>-<ulid>.json`.
Audit records are immutable (S3 Object Lock) with 400-day retention.

## Trust policy

See `trust_policy.json`. Only the broker's provisioning role can assume the
vended roles, and only when the following session tags are present:

- `openspec_proposal_id` — must match the capability's current change ID
- `ttl_expires_at` — enforced by `DateLessThan`
- `MultiFactorAuthPresent: true` for `--mode debug`
