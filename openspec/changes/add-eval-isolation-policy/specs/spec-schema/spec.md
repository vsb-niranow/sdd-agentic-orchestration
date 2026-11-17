## MODIFIED Requirements

### Requirement: SS-SR-007 — Eval contract with threshold

**Prior version:** spec-schema@v10

**Change:** add required `isolation` field (enum: `strict | advisory | none`). Add scenario
for PII-touching caps defaulting to strict.

Every capability spec that invokes a model SHALL declare `## Eval Contract` with: `set_id`,
`threshold` (float in 0..1), `metric` (defined in the eval set's manifest), and `isolation`
(enum: `strict | advisory | none`).

#### Scenario: Eval threshold missing
- **Then** OPA SHALL reject with `spec_validation.eval_threshold_missing`.

#### Scenario: `isolation: none` on PII-touching capability
- **Given** `pii_class >= 2` and `eval.isolation: none`
- **Then** OPA SHALL reject with `eval_isolation.required_for_pii`.

#### Scenario: Default isolation for PII caps
- **Given** `pii_class >= 1` and `isolation:` field absent
- **Then** OPA SHALL default to `strict` and emit `info` noting the default was applied.
