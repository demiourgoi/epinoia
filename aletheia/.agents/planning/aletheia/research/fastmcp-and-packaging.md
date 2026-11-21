# Research: FastMCP, packaging with uvx, reference project layout

Sources:
- [FastMCP docs (llms.txt index)](https://gofastmcp.com/llms.txt)
- [FastMCP tools](https://gofastmcp.com/docs/servers/tools.md)
- [FastMCP settings](https://gofastmcp.com/docs/more/settings.md)
- Reference project: [demiourgoi/Harold: harold-mcp](https://github.com/demiourgoi/Harold/tree/main/harold-mcp)

## FastMCP

- A server is built from `fastmcp.FastMCP`; tools are plain Python functions
  decorated with `@mcp.tool`. Function signatures + type hints become the
  tool input schema (Pydantic models supported); docstrings become tool
  descriptions, so docstrings must be written for an LLM caller.
- `mcp.run()` runs stdio by default — the right transport for a CLI agent.
  Tools must return promptly; for a web-URL pattern the tool returns a string
  (or structured content) with the URL and session id.
- Testing: `fastmcp.Client` with in-memory transport allows real end-to-end
  tool tests in-process (`client.call_tool(...)`).
- Settings: FastMCP reads its own `FASTMCP_*` env vars; our application
  settings use a separate `ALETHEIA_*` prefix via pydantic-settings, mirroring
  Harold's `HAROLD_*` pattern.

## Serving the GUI next to stdio MCP

- The MCP transport is stdio; the review GUI needs HTTP. FastMCP can build an
  ASGI app, but the clean approach for a stdio server is a separate
  loopback-only Starlette app started in a background daemon thread with
  uvicorn on the first session creation (lazy: zero cost until first review).
- uvicorn in a non-main thread must be stopped via its server handle, not
  signal handlers (`use_signal_handlers` off / `server.should_exit`); for an
  ephemeral per-agent process, letting the thread die with the process daemon
  thread is acceptable and simplest.

## Packaging (mirroring harold-mcp)

- `pyproject.toml` with hatchling, `requires-python = ">=3.14,<3.15"` (Python
  3.14 pinned; `.python-version` = 3.14), src layout
  (`src/aletheia_mcp`), console script `aletheia = aletheia_mcp.main:app`
  (cyclopts app, like Harold's `harold-mcp = harold_mcp.main:app`).
- Author: Juan Rodriguez <juanrh@pm.me> (same author as Harold, required).
- Static assets inside the package (`src/aletheia_mcp/webui/dist`) are
  included in the wheel automatically because they live inside the package
  dir; committed build output avoids requiring Node at install time.
- Tooling parity with Harold: ruff (120 cols, py314), mypy strict-ish,
  pytest; `uv lock` + `uv run` workflow; Makefile targets install/check/test.
- uvx invocation: `uvx --from aletheia aletheia` once published; for the
  repo checkout, `uv run aletheia` inside `aletheia/`.

## Decisions recorded

1. stdio MCP transport; Starlette+uvicorn in a lazily-started daemon thread
   for the GUI; port from `ALETHEIA_PORT`.
2. Settings via pydantic-settings with `ALETHEIA_` prefix
   (`ALETHEIA_PORT` 8417, `ALETHEIA_HOST` 127.0.0.1,
   `ALETHEIA_MAX_SESSIONS` 100).
3. Tests use `fastmcp.Client` against the real server instance plus
   Starlette's test client for the HTTP API; core logic gets plain unit
   tests against tmp_path files.
