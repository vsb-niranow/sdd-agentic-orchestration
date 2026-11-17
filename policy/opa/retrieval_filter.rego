package niranow.retrieval_filter

# Enforces SS-SR-006: any capability declaring `resources.retrieval.index` must also
# declare `resources.retrieval.retrieval_filter`.
#
# Implemented after the 2026-04-07 incident where a 6th-grade student was shown an
# 11th-grade exemplar through a RAG capability whose spec did not require a filter.
# See docs/postmortems/2026-04-retrieval-filter-leak.md.

default allow := false

allow if {
    count(deny) == 0
}

# -----------------------------------------------------------------------------
# Core rule
# -----------------------------------------------------------------------------

is_rag_capability if {
    input.spec.resources.retrieval.index
    input.spec.resources.retrieval.index != null
    input.spec.resources.retrieval.index != ""
}

deny contains msg if {
    is_rag_capability
    not input.spec.resources.retrieval.retrieval_filter
    not grace_active
    msg := sprintf(
        "retrieval_filter.required: capability '%s' declares resources.retrieval.index but omits retrieval_filter; see postmortem 2026-04-retrieval-filter-leak.md",
        [input.spec.frontmatter.capability]
    )
}

warn contains msg if {
    is_rag_capability
    not input.spec.resources.retrieval.retrieval_filter
    grace_active
    msg := sprintf(
        "retrieval_filter.grace: '%s' is in the 7-day backfill window ending %s",
        [input.spec.frontmatter.capability, input.data_bundle.grace_until.retrieval_filter]
    )
}

# -----------------------------------------------------------------------------
# Filter shape
# -----------------------------------------------------------------------------

valid_filter_kinds := {"grade_band_match", "tenant_match", "genre_match", "composite"}

deny contains msg if {
    is_rag_capability
    input.spec.resources.retrieval.retrieval_filter.kind
    not input.spec.resources.retrieval.retrieval_filter.kind in valid_filter_kinds
    msg := sprintf(
        "retrieval_filter.unknown_kind: '%s' not in %v",
        [input.spec.resources.retrieval.retrieval_filter.kind, valid_filter_kinds]
    )
}

# -----------------------------------------------------------------------------
# on_insufficient default + validity
# -----------------------------------------------------------------------------

valid_on_insufficient := {"fail", "widen_to"}

deny contains msg if {
    is_rag_capability
    input.spec.resources.retrieval.retrieval_filter.on_insufficient
    kind := kind_of(input.spec.resources.retrieval.retrieval_filter.on_insufficient)
    not kind in valid_on_insufficient
    msg := sprintf(
        "retrieval_filter.invalid_on_insufficient: got '%s'; must be 'fail' or 'widen_to: <profile>'",
        [kind]
    )
}

kind_of(v) := v if {
    is_string(v)
}
kind_of(v) := k if {
    is_object(v)
    some k
    v[k]
}

# -----------------------------------------------------------------------------
# Grace window helper
# -----------------------------------------------------------------------------

grace_active if {
    input.data_bundle.grace_until.retrieval_filter
    time.parse_rfc3339_ns(input.data_bundle.grace_until.retrieval_filter) > time.now_ns()
}
