package niranow.eval_isolation

test_strict_with_overlap_denies if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "essay-feedback", "pii_class": 2},
            "resources": {
                "model": {"arn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6-20260815-v1:0"},
                "retrieval": {"index": "arn:aws:aoss:us-east-1:111122223333:collection/rubric-exemplars-prod"}
            },
            "eval": {"set_id": "rubric_alignment_v3", "isolation": "strict"}
        },
        "data_bundle": {
            "eval_sets": {
                "rubric_alignment_v3": {
                    "isolation": "strict",
                    "source_documents": ["ex_001", "ex_002"]
                }
            },
            "index_contents": {
                "arn:aws:aoss:us-east-1:111122223333:collection/rubric-exemplars-prod": ["ex_001", "other"]
            }
        }
    }
    some msg in deny_set
    contains(msg, "index_overlap")
}

test_strict_without_overlap_allows if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "essay-feedback", "pii_class": 2},
            "resources": {
                "model": {"arn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-6-20260815-v1:0"},
                "retrieval": {"index": "arn:aws:aoss:us-east-1:111122223333:collection/rubric-exemplars-prod"}
            },
            "eval": {"set_id": "rubric_alignment_v3", "isolation": "strict"}
        },
        "data_bundle": {
            "eval_sets": {
                "rubric_alignment_v3": {
                    "isolation": "strict",
                    "source_documents": ["ex_001", "ex_002"]
                }
            },
            "index_contents": {
                "arn:aws:aoss:us-east-1:111122223333:collection/rubric-exemplars-prod": ["unrelated_doc"]
            }
        }
    }
    count(deny_set) == 0
}

test_pii2_cannot_opt_out if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "essay-feedback", "pii_class": 2},
            "resources": {"model": {"arn": "arn:aws:bedrock:us-east-1::foundation-model/x-v1:0"}},
            "eval": {"set_id": "some_set", "isolation": "none"}
        },
        "data_bundle": {"eval_sets": {}, "index_contents": {}}
    }
    some msg in deny_set
    contains(msg, "required_for_pii")
}

test_advisory_overlap_warns_not_denies if {
    deny_set := deny with input as {
        "spec": {
            "frontmatter": {"capability": "example", "pii_class": 0},
            "resources": {
                "model": {"arn": "arn:aws:bedrock:us-east-1::foundation-model/x-v1:0"},
                "retrieval": {"index": "arn:aws:aoss:us-east-1:111122223333:collection/example"}
            },
            "eval": {"set_id": "advisory_set", "isolation": "advisory"}
        },
        "data_bundle": {
            "eval_sets": {
                "advisory_set": {"isolation": "advisory", "source_documents": ["doc_a"]}
            },
            "index_contents": {
                "arn:aws:aoss:us-east-1:111122223333:collection/example": ["doc_a"]
            }
        }
    }
    count(deny_set) == 0
}
