.DEFAULT_GOAL := help
.PHONY: help test test-e2e

help: ## Show the available targets
	@echo "Available targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-10s %s\n", $$1, $$2}'

# Hermetic test suite for the whole repository (no network, no model calls).
test: ## Run the hermetic test suite
	tests/run.sh

# Hermetic suite plus the live opencode smoke tests: tiny prompts on the
# cheapest model, but they need opencode authentication and spend a few
# cents. Override the model with the E2E_MODEL and E2E_REASONING_EFFORT
# environment variables (see tests/README.md).
test-e2e: ## Run the suite plus the live opencode smoke tests
	tests/run.sh --e2e
