# Aletheia developer guide

Implementation and contribution notes. For the user-facing overview and
the Mistral Vibe setup, see [README.md](README.md).

## Architecture

```
src/aletheia_mcp/
  main.py            cyclopts CLI: default = run the MCP server (stdio),
                     `setup` subcommand installs the Vibe hook
  server/
    server.py        FastMCP instance + `run()` (stdio transport); builds
                     the MCP object on import, starts no transport
    tools/           MCP tool definitions (review_tools, system) registered
                     on `mcp`
  review/
    service.py       ReviewService: the seam between tools/HTTP and the
                     review core; one process-wide instance holds the
                     baseline (via `get_service`/`set_service`)
    baselines.py     BaselineStore: thread-safe path -> pre-edit snapshot
    diffs.py         unified_diff / has_text_change helpers
    disk.py          disk read/write/delete with clear errors
    editing.py       apply_edit: baseline-aware edit tool (exact-string
                     edit + file creation), trusted-root confinement
  web/
    server.py        loopback uvicorn in a daemon thread, started on demand
    app.py           Starlette app (the /review page and its API)
  settings.py        pydantic-settings, `ALETHEIA_*` env vars
  setup.py           install_hook: writes .vibe/hooks.toml + hook script
  webui/dist/        built React/Codemirror GUI, committed into the wheel
```

The MCP server and the review web server share one `ReviewService`: MCP
tools and the HTTP API both delegate to it, so a decision taken in the
browser reaches the agent's next `get_change_status()` poll. The review
server is **lazy** — nothing binds a port until the first baseline is
recorded.

### Key behaviours

- **Live diff.** The baseline holds a snapshot; the diff compares it with
  the current working directory at request time, so it never goes stale.
- **Constant URL, autodetected port.** `web/server.py` binds port 0 and
  reads back the OS-assigned port; `ensure_running` is idempotent and
  returns the same URL for the process lifetime.
- **In-memory state.** The baseline lives with the process (one agent
  conversation). Entries exist only while a file is under review; approve
  and reject delete them, and re-recording anchors a new round.
- **Trusted root.** The `edit` tool confines `file_path` (after resolving
  symlinks) to the git repository root of the working directory at server
  start, matching the Vibe CLI filesystem-safety criteria.

## Tool protocol (for agents)

The MCP tools the agent sees:

```
record_baseline(paths: list[str]) -> str       # before editing
get_change_status() -> str                    # live drift poll
remove_from_baseline(paths: list[str]) -> str # approve (adopt working dir)
rollback_to_baseline(paths: list[str]) -> str # reject (restore, end review)
edit(file_path, old_string, new_string, replace_all=False) -> str  # opt-in
```

- record a file **before** editing it, and re-record when a new round starts
  after a decision (error messages name the offending path);
- only UTF-8 text files are reviewable (binaries and directories are rejected
  with a clear error);
- the URL is constant for the MCP process; the port is autodetected and state
  is in-memory, living with the agent conversation.

### Opt-in `edit` tool

Agents tend to skip `record_baseline` even with the hook. The optional
**`edit`** tool is a drop-in replacement for the built-in edit **and
write_file** tools, selected by whether the target file exists:

- **existing file — edit semantics**: absolute or project-relative
  `file_path`, exact `old_string` → `new_string` replacement, unique match
  unless `replace_all`, `new_string` must differ from `old_string`;
- **missing file — creation semantics** (`write_file`): pass `old_string=""`
  and `new_string` with the full file content (non-empty; an empty file has
  nothing to review); `replace_all` is ignored. The parent directory must
  exist — the server never creates directories.

plus:

- **automatic baseline**: the first change of a file records its pre-change
  state as the review baseline (never re-anchored; repeated changes stay in
  the same round; no baseline side effects when a change fails). A created
  file gets a **creation-marker** baseline, exactly as `record_baseline` on
  a missing path: the diff shows the whole file as created, and rejecting
  the change deletes the file;
- **trusted-root confinement**: `file_path` (after resolving symlinks) must
  stay inside the trusted root — the git repository root of the working
  directory at server start (falling back to it) — matching the Vibe CLI
  filesystem-safety criteria;
- the reply also carries the review `url` to show the user.

```text
edit(file_path="/repo/src/main.py", old_string="x = 1", new_string="x = 2")
→ {"file": "...", "message": "Replaced 1 occurrence(s) ...", "created": false,
   "old_string": "x = 1", "new_string": "x = 2", "baseline_registered": true,
   "url": "http://127.0.0.1:53412/review"}
edit(file_path="/repo/src/new_file.py", old_string="", new_string="print('hi')\n")
→ {"file": "...", "created": true, "message": "Created ...",
   "baseline_registered": true, "url": "http://127.0.0.1:53412/review"}
```

Vibe exposes MCP tools prefixed with the server name, so `edit` appears as
`aletheia_edit`. Hosts disable both built-ins (`disabled_tools = ["edit",
"write_file"]`, see the README setup); this is the primary enforcement
mechanism, with the reminder hook (below) as a best-effort fallback for the
remaining channels (shell commands, other MCP servers).

## Vibe hook placement

`aletheia setup` installs a `post_tool` hook (`.vibe/hooks.toml` +
`.vibe/hooks/aletheia_baseline.py`) matching `re:edit|write_file`. The
project-level hook is written to the `.vibe/` of the **git repository root**,
not the current directory, because Vibe trusts and loads project
configuration from the repository root (the same placement rule epinoia
applies to `.opencode/` files). `setup` resolves the git root of the given
directory and reports where it installed. Installation is merge-safe and
idempotent (keyed on the unique hook name `aletheia-baseline`).

The hook is best-effort coaching: it runs in its own process and cannot
inspect the server's in-memory baseline, so it makes a skipped baseline a
visible agent mistake rather than a silent one. It is the **fallback**
enforcement mechanism: disabling the built-in `edit` and `write_file`
tools (README setup, step 2) is stronger — changes then can only flow
through Aletheia's baseline-aware `edit` tool, which records the baseline
in the same call. Keep the hook for the channels that disabling cannot
close (shell commands, other MCP servers).

## Build and check

Requires [uv](https://docs.astral.sh/uv/) (Python 3.14) and, for the GUI,
Node/npm.

```console
make install   # uv sync (Python 3.14)
make webui     # build the review GUI (npm + Vite) into the package
make check     # uv lock --locked + mypy + ruff check/format
make test      # pytest (unit + real-server end-to-end)
make run       # run the aletheia CLI from the checkout (`uv run aletheia`)
```

Running without the checkout: `uvx --from aletheia aletheia` (once
published).

### The web UI

`webui/` is Vite + React + TypeScript, using CodeMirror 6's merge view for
the side-by-side diff. `make webui` runs `npm ci && npm run build` and
copies the license/asset sidecars into `src/aletheia_mcp/webui/dist`. That
built output is **committed** to `src/aletheia_mcp/webui/dist` so the
published wheel ships the GUI without requiring Node at install time —
rebuild and commit it whenever the UI changes.

## Tests

```console
make test
```

- `tests/unit/` — baselines, diffs, disk, editing, service, settings,
  setup (hook installer merge/idempotency, plus the hook script run over
  synthetic payloads), web API, and the CLI.
- `tests/integration/test_e2e.py` — drives the MCP tools over a real
  `fastmcp` client against the real loopback web server and real disk
  effects.

There is no separate hermetic/e2e split: the end-to-end test uses only
loopback sockets and never the network.

## Packaging

`pyproject.toml` builds with hatchling (`src/aletheia_mcp` is the wheel
package; `src/aletheia_mcp/webui/dist` is included as an sdist artifact).
The console script `aletheia` maps to `aletheia_mcp.main:app`. Ruff targets
`py314`, line length 120; mypy runs over `src` with untrusted defs
disallowed.

> **Interpreter caveat.** The project pins Python 3.14. `setup.py` relies on
> Python 3.14's parenthesised-optional `except` syntax; under Python ≤3.13
> the module fails to import and `aletheia setup` cannot start. Keep the
> pin (or parenthesise the `except` clause) if you broaden support.

## License and provenance

Original code is MIT (see [LICENSE](LICENSE)).

The review GUI is built with [React](https://react.dev/) and
[CodeMirror 6](https://codemirror.net/) (merge view), both MIT-licensed; the
build tool is [Vite](https://vite.dev/). Third-party components are tracked
in [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md) at the repository
root, and every file carries a REUSE annotation in `REUSE.toml`.
