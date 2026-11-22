# Contributing to Aletheia

- Python toolchain is managed with `uv` and pinned to Python 3.14
  (`.python-version`). `make install` creates the environment.
- `make check` runs mypy and ruff; `make test` runs pytest (unit + a
  real-server end-to-end test); `make webui` rebuilds the review GUI from
  `webui/` into `src/aletheia_mcp/webui/dist` (committed so the wheel
  ships without Node).
- Design docs and the implementation plan live in `.agents/planning/`;
  the PDD skill (see `skills/pdd`) governs changes that touch the design.
- Commits follow the repo style: lowercase scope prefix, e.g.
  `aletheia: add <change>`.
