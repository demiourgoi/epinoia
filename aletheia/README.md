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
   compact **side-by-side diff** per file (red/green changed chunks,
   minimal margins — the diff is the product). They can **approve** a
   file (adopt the working directory), **edit** the proposed content and
   then approve, or **reject** it (restore the pre-change content on
   disk) — per file, or the whole change at once. Language-dependent
   syntax highlighting is out of scope for this MVP (diff highlighting
   covers review needs).
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
edit(file_path, old_string, new_string, replace_all=False) -> str  # opt-in
```

### Opt-in `edit` tool (recommended)

In practice agents tend to skip `record_baseline` even with the hook.
The optional **`edit`** tool is a drop-in replacement for the built-in
edit tool: same schema *and* semantics as Vibe's built-in edit
(`file_path` absolute, exact `old_string` → `new_string` replacement,
unique match unless `replace_all`, `new_string` must differ), plus:

- **automatic baseline**: the first edit of a file records its pre-edit
  content as the review baseline (never re-anchored; repeated edits stay
  in the same round; no baseline side effects when an edit fails);
- **trusted-root confinement**: `file_path` (after resolving symlinks)
  must stay inside the trusted root — the git repository root of the
  working directory at server start (falling back to it) — matching the
  Vibe CLI filesystem-safety criteria;
- the reply also carries the review `url` to show the user.

```text
edit(file_path="/repo/src/main.py", old_string="x = 1", new_string="x = 2")
→ {"file": "...", "message": "edited", "baseline_registered": true,
   "old_string": "x = 1", "new_string": "x = 2", "url": "http://127.0.0.1:53412/review"}
```

Both flows coexist: keep the built-in edit tool plus the hook reminder,
or forbid the built-in edit tool so the agent can only edit through
Aletheia's baseline-aware one.

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

## Replacing the built-in edit tool (Mistral Vibe)

To make agents edit *only* through the baseline-aware `edit` tool, forbid
the built-in one in your Vibe configuration (project `./.vibe/config.toml`
at the git root, or user `~/.vibe/config.toml`; per the
[Vibe configuration reference](https://docs.mistral.ai/vibe/code/cli/configuration-reference)):

```toml
disabled_tools = ["edit"]
# or, equivalently:
[tools.edit]
permission = "never"
```

The same keys work in a custom agent file (`.vibe/agents/<name>.toml`),
so you can scope the restriction to a single agent. Add Aletheia to the
same `config.toml` if you have not yet (see the
[MCP servers docs](https://docs.mistral.ai/vibe/code/cli/mcp-servers)):

```toml
[[mcp_servers]]
name = "aletheia"
transport = "stdio"
command = "uvx"
args = ["--from", "aletheia", "aletheia"]

# then, to force edits through it:
disabled_tools = ["edit"]
```

Vibe exposes MCP tools prefixed with the server name — ours appears as
`aletheia_edit` — so `disabled_tools = ["edit"]` forbids only the
built-in edit tool and leaves Aletheia's untouched. With the built-in
tool gone, editing through `aletheia_edit` registers the baseline
automatically so nothing can be skipped; keep `aletheia setup` for the
reminder hook if you want belt and braces for the other ways agents can
still change files (`write_file`, shell commands).

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
merge view for the side-by-side diff). Its built output is committed to
`src/aletheia_mcp/webui/dist` so the published wheel ships the GUI
without requiring Node at install time.

## Screenshots

Full-width review page, dark + orange theme (palette from Mistral's
own docs assets: `#131313` background, `#ef9743` orange accents,
the `#ffaf00 → #e10500` brand gradient on the title), with the
compact side-by-side diff (red/green changed chunks down-tuned for
dark; language-dependent highlighting is out of the MVP):

| Java file under review | Python file under review |
| --- | --- |
| ![Java diff with red/green changed chunks](docs/screenshots/review-diff-java.png) | ![Python diff with red/green changed chunks](docs/screenshots/review-diff-python.png) |

## Third-party components

The review GUI is built with [React](https://react.dev/) and
[CodeMirror 6](https://codemirror.net/) (merge view), both MIT-licensed; the build tool is [Vite](https://vite.dev/). See
[THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md) at the repository root
for the monorepo policy.

## License

MIT — see [LICENSE](LICENSE).
