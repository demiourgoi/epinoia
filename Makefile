.PHONY: test test-e2e

# Hermetic test suite for the whole repository (no network, no model calls).
test:
	tests/run.sh

# Hermetic suite plus the live opencode smoke tests: tiny prompts on the
# cheapest model, but they need opencode authentication and spend a few
# cents. Override the model with the E2E_MODEL and E2E_REASONING_EFFORT
# environment variables (see tests/README.md).
test-e2e:
	tests/run.sh --e2e
