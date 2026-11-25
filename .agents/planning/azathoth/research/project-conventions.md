# Research: project scaffolding conventions (harold-mcp reference)

Source: https://github.com/demiourgoi/Harold/tree/main/harold-mcp
(requester-specified reference for the Python/uv project layout).

## Findings

`harold-mcp` is the canonical demiourgoi Python service layout:

- **uv project**: `pyproject.toml` with `requires-python = ">=3.14,<3.15"`,
  `.python-version` pinned to `3.14`, `uv.lock` committed, `uv sync` install,
  dependency groups for dev tooling.
- **src layout**: package code under `src/<package_name>/` (import name
  `harold_mcp`), `tests/unit/` and `tests/integration/` split, pytest
  configured via `[tool.pytest.ini_options]` `testpaths = ["tests"]`.
- **Entry points**: `[project.scripts]` console script calling a tiny
  `main.py` that delegates to the server runner.
- **Tooling** (all wired into `make check`): `ruff` (py314 target, wide rule
  selection, preview formatting), `mypy` strict-ish (`disallow_untyped_defs`,
  `warn_return_any`, ...), `deptry` for obsolete deps, `uv lock --locked`.
- **Settings**: `pydantic-settings` `BaseSettings` reading `<PREFIX>_*`
  environment variables, defaults computed in helper functions.
- **Makefile**: `install`, `check`, `test`, `test-unit`, `test-integration`,
  `run` targets with 🚀 echo banners.
- **Hatchling** build backend with `packages = ["src/<pkg>"]`.

## Consequence for azathoth

`azathoth/` mirrors this layout with `AZATHOTH_*` settings variables,
`src/azathoth/` package, `tests/unit` (hermetic, run by the repo's default
test flow) and `tests/integration` (live `vibe-acp` smoke tests, excluded by
default like the repo's e2e suites), plus the same Makefile target names.
Dev tooling is kept but trimmed to what is exercised here: ruff, mypy,
pytest, deptry.
