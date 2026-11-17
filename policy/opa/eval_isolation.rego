package niranow.eval_isolation

# Enforces SS-SR-007 (modified): eval contract isolation + no overlap between a
# capability's retrieval index and a strict-isolation eval set's source documents.
#
# Implemented after the 2026-06 CI-vs-prod divergence incident (eval leakage).
# See docs/postmortems/2026-06-eval-leakage.md.

default allow := false

allow if {
    count(deny) == 0
}

# -----------------------------------------------------------------------------
# isolation field required when model is invoked
# -----------------------------------------------------------------------------

deny contains msg if {
    input.spec.resources.model
    input.spec.resources.model.arn
    not input.spec.eval.isolation
    pii := input.spec.frontmatter.pii_class
    pii >= 1
    msg := sprintf(
        "eval_isolation.required: capability '%s' (pii_class=%d) must declare eval.isolation; default is 'strict'",
        [input.spec.frontmatter.capability, pii]
    )
}

# -----------------------------------------------------------------------------
# PII caps may not opt out
# -----------------------------------------------------------------------------

deny contains msg if {
    input.spec.eval.isolation == "none"
    input.spec.frontmatter.pii_class >= 2
    msg := sprintf(
        "eval_isolation.required_for_pii: capability '%s' has pii_class=%d; isolation: none is forbidden",
        [input.spec.frontmatter.capability, input.spec.frontmatter.pii_class]
    )
}

# -----------------------------------------------------------------------------
# Index must not intersect strict-isolation eval set's source documents
# -----------------------------------------------------------------------------

deny contains msg if {
    input.spec.eval.isolation == "strict"
    index := input.spec.resources.retrieval.index
    set_id := input.spec.eval.set_id
    set := input.data_bundle.eval_sets[set_id]
    set.isolation == "strict"

    some doc_id in set.source_documents
    doc_id in input.data_bundle.index_contents[index]

    msg := sprintf(
        "eval_isolation.index_overlap: eval case document '%s' is present in index '%s' used by capability '%s'; isolation: strict forbids overlap",
        [doc_id, index, input.spec.frontmatter.capability]
    )
}

# -----------------------------------------------------------------------------
# Advisory isolation: warn on overlap instead of deny
# -----------------------------------------------------------------------------

warn contains msg if {
    input.spec.eval.isolation == "advisory"
    index := input.spec.resources.retrieval.index
    set_id := input.spec.eval.set_id
    set := input.data_bundle.eval_sets[set_id]

    some doc_id in set.source_documents
    doc_id in input.data_bundle.index_contents[index]

    msg := sprintf(
        "eval_isolation.advisory_overlap: '%s' overlaps eval set '%s'; advisory isolation permits this, consider promoting to strict",
        [doc_id, set_id]
    )
}
