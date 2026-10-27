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
# discovers project skills). The opencode agent plus its config go to the git
# root of TARGET_DIR, or to TARGET_DIR itself when it is not inside a git
# repository: opencode discovers .opencode directories from its working
# directory up to the filesystem root, and the review script runs opencode at
# the repository root, so the files must live there to be found. Existing
# files are overwritten; other files in the target are left untouched.
install: ## Install skills + opencode agent/config (opencode files go to the target's git root)
	@if [ -z "$(TARGET_DIR)" ]; then \
		echo "Error: could not determine TARGET_DIR (PWD is unset or empty); pass it explicitly, for example: make install TARGET_DIR=../my-project" >&2; \
		exit 2; \
	fi; \
	if [ ! -d "$(TARGET_DIR)" ]; then \
		echo "Error: target directory does not exist: $(TARGET_DIR)" >&2; \
		exit 2; \
	fi; \
	OPENCODE_DIR="$$(git -C "$(TARGET_DIR)" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$(TARGET_DIR)")"; \
	if [ "$$(cd "$$OPENCODE_DIR" && pwd -P)" = "$$(cd "$(REPO_DIR)" && pwd -P)" ]; then \
		echo "Error: TARGET_DIR is this repository (or resolves to it); choose the project to install into" >&2; \
		exit 2; \
	fi; \
	mkdir -p "$(TARGET_DIR)/.agents/skills"; \
	cp -R "$(REPO_DIR)/skills/." "$(TARGET_DIR)/.agents/skills/"; \
	mkdir -p "$$OPENCODE_DIR/.opencode"; \
	cp -R "$(REPO_DIR)/.opencode/." "$$OPENCODE_DIR/.opencode/"; \
	echo "Installed skills:         $(TARGET_DIR)/.agents/skills"; \
	echo "Installed opencode agent: $$OPENCODE_DIR/.opencode"

# Hermetic test suite for the whole repository (no network, no model calls).
test: ## Run the hermetic test suite
	tests/run.sh

# Hermetic suite plus the live opencode smoke tests: tiny prompts on the
# cheapest model, but they need opencode authentication and spend a few
# cents. Override the model with the E2E_MODEL and E2E_REASONING_EFFORT
# environment variables (see tests/README.md).
test-e2e: ## Run the suite plus the live opencode smoke tests
	tests/run.sh --e2e
