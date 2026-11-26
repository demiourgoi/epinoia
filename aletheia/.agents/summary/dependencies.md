# Dependencies — aletheia

<!-- tags: dependencies, stack -->

From `pyproject.toml` (runtime), the dev dependency group, and
`webui/package.json` (GUI).

## Python runtime dependencies

<!-- tags: python, runtime-deps -->

| Package | Version | Used for |
| --- | --- | --- |
| `fastmcp` | >=4.0.0 | The MCP server framework: `FastMCP` instance, `@mcp.tool` decorators, stdio transport; tests drive it with `fastmcp.Client` |
| `cyclopts` | >=4.23.0 | The `aletheia` CLI (`App`, default command, `setup` subcommand, `--global` flag) |
| `pydantic` | >=2.13.4 | Base for settings models |
| `pydantic-settings` | >=2.15.0 | `Settings` reading `ALETHEIA_*` env vars (`BaseSettings`, `SettingsConfigDict(env_prefix="ALETHEIA_")`) |
| `starlette` | >=0.48.0 | The review web app: routes, middleware (`LoopbackGuard`), `StaticFiles`, JSON/file responses |
| `uvicorn` | >=0.38.0 | ASGI server running the Starlette app in a daemon thread on a loopback, OS-assigned port |

Standard library carries the rest: `difflib` (unified diffs), `tempfile` +
`os.replace` (atomic writes), `threading` (locks, server thread), `subprocess`
(git root lookup), `json` (tool results).

## Python dev dependencies

<!-- tags: python, dev-deps -->

| Package | Version | Used for |
| --- | --- | --- |
| `pytest` | >=9.0.2 | test runner (`tests/`; `testpaths = ["tests"]`) |
| `mypy` | >=1.19.1 | type checking over `src` (`disallow_untyped_defs`, `check_untyped_defs`, `warn_return_any`, …; uvicorn imports ignored) |
| `ruff` | >=0.15.7 | lint + format; target `py314`, line length 120, rule set YTT/S/B/A/C4/T10/SIM/I/C90/E/W/F/PGH/UP/RUF/TRY; tests relax S101/S310/S603; `.agents` excluded |

Test-only: `anyio` and `fastmcp.Client` are used by the e2e test (pulled in
via fastmcp/pytest ecosystems as needed).

## Build / packaging

- **hatchling** build backend; wheel packages `src/aletheia_mcp`; sdist adds
  `src/aletheia_mcp/webui/dist` as an artifact (the committed GUI bundle).
- Console script: `aletheia = "aletheia_mcp.main:app"`.
- Toolchain: **uv** for env/lock (`uv.lock`, `uv sync`, `uv lock --locked`),
  Python pinned to 3.14 (`.python-version`, `requires-python = ">=3.14,<3.15"`).

## GUI (`webui/package.json`)

<!-- tags: gui, npm-deps -->

| Package | Version | Used for |
| --- | --- | --- |
| `react`, `react-dom` | ^18.3.1 | the review page UI |
| `@codemirror/merge`, `@codemirror/state`, `@codemirror/view` | ^6.x | side-by-side merge diff view with an editable right pane |
| `vite`, `@vitejs/plugin-react` | ^6 / ^4 | dev server + production build (`tsc -b && vite build`) |
| `typescript`, `@types/react`, `@types/react-dom` | ^5.7 / ^18 | type checking of the GUI sources |

Third-party GUI components (React, CodeMirror 6, Vite — all MIT) are tracked
in the repository-root `THIRD-PARTY-NOTICES.md` and `REUSE.toml`; the built
bundle carries a `LICENSE` sidecar copied by `make webui`.

## Why these choices (design rationale)

- **FastMCP over a hand-rolled MCP loop**: the project is an MCP server, and
  FastMCP gives the tool decorator model, stdio transport, and a test client
  for free.
- **Starlette + uvicorn for the GUI backend**: minimal ASGI stack already in
  the dependency footprint of an MCP server; the `LoopbackGuard` middleware
  pattern maps directly onto Starlette middleware.
- **CodeMirror 6 merge view**: gives the side-by-side diff with an editable
  pane (user tweaks before approving) out of the box.
- **Committed dist bundle**: the published wheel must serve the GUI without
  requiring Node at install time, so `make webui` output is checked in.
- **In-memory baseline**: review state belongs to one agent conversation;
  nothing needs to survive the process, and an in-memory store keeps the
  diff logic trivially consistent (single process, lock-guarded).
