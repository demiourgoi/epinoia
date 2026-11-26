.PHONY: install webui check test run
install: ## Install the virtual environment (Python 3.14)
	@echo "🚀 Creating virtual environment using uv"
	@uv sync

webui: ## Build the review web GUI into the package
	@echo "🛠️ Building the web UI"
	cd webui && npm ci && npm run build
	cp webui/dist-sidecar/LICENSE src/aletheia_mcp/webui/dist/LICENSE
	cp webui/dist-sidecar/assets/README.md src/aletheia_mcp/webui/dist/assets/README.md

check: ## Run code quality tools
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Static type checking: Running mypy"
	@uv run mypy
	@uv run ruff check --exit-non-zero-on-fix
	@uv run ruff format

test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run python -m pytest

run: ## Run the aletheia CLI
	@uv run aletheia
