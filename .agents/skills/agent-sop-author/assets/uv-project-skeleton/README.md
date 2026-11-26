# skill-scripts

Python scripts and helpers for `<skill-name>` that need third-party
dependencies. Managed as a uv project: add dependencies to
`pyproject.toml` and run scripts with `uv run <script>`.

Skeleton copied from `.agents/skills/agent-sop-author/assets/uv-project-skeleton/`.

If your scripts have no tests, remove the `dev` dependency group and the
`[tool.pytest.ini_options]` section before copying, so `uv run pytest`
does not fail for lack of a `tests/` directory.
