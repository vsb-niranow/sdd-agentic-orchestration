# Tasks — tighten-prompt-spec-coupling

## 1. Prompt registry schema
- [ ] Document `prompts/registry.yaml` schema in `docs/spec-schema.md`
  - Fields per prompt_id: `latest`, `versions: [{v, sha256, owner_capability, created}]`

## 2. Spec-lint rule
- [ ] Implement `tools/spec-lint/rules/prompt_registry_coherent.py`
  - Computes SHA-256 of each `prompts/<id>_v<N>.md`
  - Compares to registry's recorded hash
  - Fails with a precise error message on mismatch

## 3. CI workflow
- [ ] Add `.github/workflows/prompt-delta-coupling.yaml`
  - Computes the set of changed files under `prompts/`
  - For each, looks up the owning capability in registry
  - Requires `openspec/changes/<id>/specs/<cap>/spec.md` to be in the same PR
  - Fails with annotation pointing to the orphan prompt change

## 4. OPA rule
- [ ] Author `policy/opa/prompt_versioning.rego`
  - On merged proposals, verify the capability's declared `prompt_id@vN` matches the registry

## 5. AI reviewer training
- [ ] Add directive to `tools/ai-reviewer/prompts/spec_diff_reviewer_v2.md`
  - Check prompt content hash vs. spec-declared version before semantic analysis
  - Short-circuit with a specific error class (`prompt_hash_mismatch`) rather than a generic
    "un-specced behavior" flag
