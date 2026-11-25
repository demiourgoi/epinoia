.PHONY: install
install: ## Install the virtual environment
	@echo "🚀 Creating virtual environment using uv"
	@uv sync

.PHONY: check
check: ## Run code quality tools
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@uv run ruff check --exit-non-zero-on-fix
	@uv run ruff format
	@echo "🚀 Static type checking: Running mypy"
	@uv run mypy
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@uv run deptry src

.PHONY: test
test: ## Test the code with pytest (hermetic unit tests only)
	@echo "🚀 Testing code: Running pytest"
	@uv run python -m pytest tests/unit

.PHONY: test-unit
test-unit: ## Run the hermetic unit tests
	@uv run python -m pytest tests/unit

.PHONY: test-integration
test-integration: ## Run the live ACP agent tests (needs AZATHOTH_INTEGRATION_ACP_COMMAND)
	@uv run python -m pytest tests/integration -v

.PHONY: run
run: ## Run the server
	@echo "🚀 Running server"
	@uv run azathoth
