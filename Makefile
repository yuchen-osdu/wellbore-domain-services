.DEFAULT_GOAL := gen-requirements

.PHONY: gen-requirements
gen-requirements:
	./scripts/regenerate-requirements.sh
