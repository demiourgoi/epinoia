# Aletheia

**Aletheia** (ἀλήθεια: unconcealment) is an MCP server that gives terminal
coding agents (such as Mistral Vibe CLI) the Zed-style **asynchronous
change review** workflow:

1. The agent calls **`record_baseline(paths)`** *before* editing: the
   server snapshots the current content of those files (files that will be
   created are recorded as such). The review web server starts on first
   use and the tool returns its **constant URL** to show the user.
2. The agent **edits the files normally**. Changes are on disk, so linters
   and tests can verify them at any time. The review diff is **live**: it
   always compares the baseline with the current working directory.
3. The user opens the URL in a browser: a local web GUI shows a
   **side-by-side, syntax-highlighted diff** per file (Java, Python,
   TypeScript, …). They can **approve** a file (adopt the working
   directory), **edit** the proposed content and then approve, or
   **reject** it (restore the pre-change content on disk) — per file, or
   the whole change at once.
4. Decisions shrink the baseline: **a file is under review only while it
   has a baseline entry**. After approve or reject the file leaves review;
   if the agent edits it again in a later round, it records the baseline
   again — that is also how a new change set is anchored, like Zed's
   per-turn review.
5. The agent can poll **`get_change_status()`** at any time — the review
   never blocks the conversation.

```mermaid
sequenceDiagram
    participant U as User
    participant A as CLI agent
    participant M as Aletheia MCP (stdio)
    participant W as Review GUI (loopback HTTP, free port)
    A->>M: record_baseline(files) — starts W, returns URL
    A->>A: edits files on disk, runs linters
    A->>U: shows the constant URL
    U->>W: reviews live highlighted diffs
    U->>W: approve (adopt) / edit+save / reject (rollback)
    W->>W: rejected files restored on disk, out of review
    A->>M: get_change_status()
    M-->>A: live drift; decided files gone from the baseline
```

## Tool protocol (for agents)

```
record_baseline(paths: list[str]) -> str       # before editing
get_change_status() -> str                    # live drift poll
remove_from_baseline(paths: list[str]) -> str # approve (adopt working dir)
rollback_to_baseline(paths: list[str]) -> str # reject (restore, end review)
```

Typical loop:

```text
record_baseline(["src/main.py", "src/new_file.py"])
→ {"url": "http://127.0.0.1:53412/review", "recorded": [...], "marked_for_creation": [...]}
(edit src/main.py; create src/new_file.py; run tests — show the URL to the user)
get_change_status()
→ {"files": [{"path": "...", "kind": "modified", "changed": true}, ...]}
(when the user approves: e.g. remove_from_baseline(...) or the GUI button)
```

Rules:
- record a file **before** editing it and re-record when a new change
  round starts after a decision (error messages name the offending path);
- only UTF-8 text files are reviewable (binary files and directories are
  rejected with a clear error);
- the URL is constant for the MCP process; the port is **autodetected**
  (no port configuration), and state is in-memory: it lives with the agent
  conversation;
- baseline entries live exactly as long as the file is under review.

## Vibe hook (baseline reminder)

`aletheia setup` installs a `post_tool` hook into `.vibe/hooks.toml`
(merge-safe, idempotent) that reminds the agent to
`record_baseline` every path it edits:

```console
uv run aletheia setup            # project-level: .vibe/ at the git root
uv run aletheia setup --global   # user-level (~/.vibe/)
```

The project-level hook is installed into the `.vibe/` directory of the
**git repository root** — not the current directory — because Vibe trusts
and loads project configuration from the repository root (the same
placement rule epinoia applies to `.opencode/` files: installing inside a
subdirectory would make them undiscoverable). `setup` resolves the git
root of the given directory and tells you where it installed.

Best-effort coaching: the hook runs in its own process and cannot inspect
the server's in-memory baseline; it makes skipping the baseline a visible
agent mistake rather than a silent one.

## Run

```console
uv run aletheia            # stdio MCP server (repo checkout)
uvx --from aletheia aletheia   # once published
```

Client configuration (any MCP host that supports stdio):

```json
{
  "mcpServers": {
    "aletheia": { "command": "uvx", "args": ["--from", "aletheia", "aletheia"] }
  }
}
```

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `ALETHEIA_HOST` | `127.0.0.1` | bind host of the review web GUI (loopback only by default) |

There is no port setting: the review server binds an OS-assigned free
port and the URL is returned by `record_baseline`. The review page lives
at `/review` (the bare root redirects there), leaving the URL space free
for future pages.

## Development

```console
make install   # uv sync (Python 3.14)
make webui     # build the review GUI (npm + Vite) into the package
make check     # mypy + ruff
make test      # pytest (unit + real-server end-to-end)
```

The web UI lives in `webui/` (Vite + React + TypeScript, CodeMirror 6
with the merge view and `@codemirror/language-data` for syntax
highlighting). Its built output is committed to
`src/aletheia_mcp/webui/dist` so the published wheel ships the GUI
without requiring Node at install time.

## Screenshots

| Java file under review | Python file under review |
| --- | --- |
| ![Java diff with syntax highlighting and red/green changed chunks](docs/screenshots/review-diff-java.png) | ![Python diff with syntax highlighting](docs/screenshots/review-diff-python.png) |

## Third-party components

The review GUI is built with [React](https://react.dev/) and
[CodeMirror 6](https://codemirror.net/) (merge view + language data), both
MIT-licensed; the build tool is [Vite](https://vite.dev/). See
[THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md) at the repository root
for the monorepo policy.

## License

MIT — see [LICENSE](LICENSE).
