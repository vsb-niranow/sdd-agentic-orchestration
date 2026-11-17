package niranow.retrieval_filter

# Unit tests for retrieval_filter.rego. Run with `opa test policy/opa -v`.

test_rag_without_filter_denies if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "example-cap"},
            "resources": {
                "retrieval": {
                    "index": "arn:aws:aoss:us-east-1:111122223333:collection/example",
                }
            }
        },
        "data_bundle": {"grace_until": {}}
    }
    count(deny_set) > 0
}

test_rag_with_filter_allows if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "example-cap"},
            "resources": {
                "retrieval": {
                    "index": "arn:aws:aoss:us-east-1:111122223333:collection/example",
                    "retrieval_filter": {
                        "kind": "grade_band_match",
                        "source_field": "submission.grade_band",
                        "target_field": "exemplar.grade_band",
                        "on_insufficient": "fail"
                    }
                }
            }
        },
        "data_bundle": {"grace_until": {}}
    }
    count(deny_set) == 0
}

test_non_rag_capability_unaffected if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "non-rag"},
            "resources": {"retrieval": null}
        },
        "data_bundle": {"grace_until": {}}
    }
    count(deny_set) == 0
}

test_invalid_filter_kind_denies if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "example-cap"},
            "resources": {
                "retrieval": {
                    "index": "arn:aws:aoss:us-east-1:111122223333:collection/example",
                    "retrieval_filter": {"kind": "made_up_kind"}
                }
            }
        },
        "data_bundle": {"grace_until": {}}
    }
    some msg in deny_set
    contains(msg, "unknown_kind")
}

test_invalid_on_insufficient_denies if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "example-cap"},
            "resources": {
                "retrieval": {
                    "index": "arn:aws:aoss:us-east-1:111122223333:collection/example",
                    "retrieval_filter": {
                        "kind": "grade_band_match",
                        "on_insufficient": "silently_widen"
                    }
                }
            }
        },
        "data_bundle": {"grace_until": {}}
    }
    some msg in deny_set
    contains(msg, "invalid_on_insufficient")
}
