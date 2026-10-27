.DEFAULT_GOAL := help
.PHONY: help install test test-e2e

# Directory of this Makefile, so install sources resolve no matter how make
# is invoked (-C or -f).
REPO_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

# Default install destination: the caller's directory. make imports PWD from
# the environment and does not rewrite it when -C changes directory, so
# `cd project && make -C this-repo install` installs into project.
TARGET_DIR ?= $(PWD)

help: ## Show the available targets
	@echo "Available targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-10s %s\n", $$1, $$2}'

# Copy the distributable skills into TARGET_DIR/.agents/skills/ (where Zed
# discovers project skills) and the opencode agent plus its config into
# TARGET_DIR/.opencode/ (where opencode discovers agents and project config).
# Existing files are overwritten; other files in the target are left
# untouched.
install: ## Install skills + opencode agent/config into TARGET_DIR (default: caller's PWD)
	@if [ -z "$(TARGET_DIR)" ]; then \
		echo "Error: could not determine TARGET_DIR (PWD is unset or empty); pass it explicitly, for example: make install TARGET_DIR=../my-project" >&2; \
		exit 2; \
	fi; \
	if [ ! -d "$(TARGET_DIR)" ]; then \
		echo "Error: target directory does not exist: $(TARGET_DIR)" >&2; \
		exit 2; \
	fi; \
	if [ "$$(cd "$(TARGET_DIR)" && pwd -P)" = "$$(cd "$(REPO_DIR)" && pwd -P)" ]; then \
		echo "Error: TARGET_DIR is this repository; choose the project to install into, or pass TARGET_DIR explicitly" >&2; \
		exit 2; \
	fi
	mkdir -p "$(TARGET_DIR)/.agents/skills"
	cp -R "$(REPO_DIR)/skills/." "$(TARGET_DIR)/.agents/skills/"
	mkdir -p "$(TARGET_DIR)/.opencode"
	cp -R "$(REPO_DIR)/.opencode/." "$(TARGET_DIR)/.opencode/"
	@echo "Installed skills:         $(TARGET_DIR)/.agents/skills"
	@echo "Installed opencode agent: $(TARGET_DIR)/.opencode"

# Hermetic test suite for the whole repository (no network, no model calls).
test: ## Run the hermetic test suite
	tests/run.sh

# Hermetic suite plus the live opencode smoke tests: tiny prompts on the
# cheapest model, but they need opencode authentication and spend a few
# cents. Override the model with the E2E_MODEL and E2E_REASONING_EFFORT
# environment variables (see tests/README.md).
test-e2e: ## Run the suite plus the live opencode smoke tests
	tests/run.sh --e2e
