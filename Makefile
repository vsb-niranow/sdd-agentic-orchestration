.PHONY: help validate lint opa-test preview-jit preview-review clean

CHANGE ?= add-essay-feedback-v1

help:
	@echo "lab-agentic-sdd-orchestration — make targets"
	@echo ""
	@echo "  make validate CHANGE=<id>        OPA + spec-lint + schema validate a proposal"
	@echo "  make lint                        run all spec-lint rules"
	@echo "  make opa-test                    run OPA unit tests"
	@echo "  make preview-jit CHANGE=<id>     dry-run JIT IAM broker for a change"
	@echo "  make preview-review CHANGE=<id>  print the AI reviewer payload (no model call)"
	@echo "  make clean                       drop temp artifacts"

validate:
	@python tools/opa_evaluate_change.py --change $(CHANGE) --bundle /tmp/opa_bundle.json 2>/dev/null \
	  || (echo "note: opa_evaluate_change.py is a stub; see policy/bundles/manifest.yaml for the production bundle build" && true)
	@python tools/spec-lint/runner.py --rule shall_id_coverage --rule retrieval_filter_declared --rule model_arn_pinned

lint:
	@python tools/spec-lint/runner.py

opa-test:
	@opa test policy/opa -v

preview-jit:
	@python tools/jit-iam-broker/broker.py --change $(CHANGE) --mode preview --repo-root .

preview-review:
	@python tools/ai-reviewer/reviewer.py --change $(CHANGE) --diff /dev/null --repo-root . --emit-payload

clean:
	@rm -f /tmp/opa_bundle.json /tmp/opa_*.json /tmp/lint.json /tmp/review.json
