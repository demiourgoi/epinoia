# Aletheia

**Aletheia** (ἀλήθεια: unconcealment) is an MCP server that gives terminal
coding agents (such as Mistral Vibe CLI) the Zed-style **asynchronous change
review** workflow:

1. **`record_baseline`** — before editing, the agent records the files it
   will touch. The server snapshots their current content in memory (files
   that will be created are recorded as such).
2. The agent **edits the files normally**. The changes are on disk, so
   linters and tests can verify them at any time.
3. **`open_review`** — the server computes the diff of every changed file
   against its baseline, creates an in-memory review session, and returns a
   URL the agent can show to the user. **The call never blocks.**
4. The user opens the URL: a local web GUI shows a **side-by-side,
   syntax-highlighted diff** of each file (Java, Python, TypeScript, …). They
   can **approve** each file, **edit** the proposed content and then approve,
   or **reject** it — per file, or the whole set.
   - **approve** keeps the file as it is on disk;
   - **save edit** writes the user's modified content to disk;
   - **reject** rolls the file back to its pre-agent content **on disk
     immediately** (created files are deleted).
5. **`get_review_status`** — the agent can poll the session to learn which
   files were approved, edited, or rejected (and reverted).

```mermaid
sequenceDiagram
    participant U as User
    participant A as CLI agent
    participant M as Aletheia MCP (stdio)
    participant W as Review GUI (loopback HTTP)
    A->>M: record_baseline(files)
    A->>A: edits files on disk, runs linters
    A->>M: open_review(files)
    M-->>A: session_id + review URL
    A->>U: shows the URL
    U->>W: reviews highlighted diffs
    U->>W: approve / edit+save / reject (per file or all)
    W->>W: rejected changes reverted on disk
    A->>M: get_review_status(session_id)
    M-->>A: decisions; rejected files are back to baseline
```

## Tool protocol (for agents)

```
record_baseline(paths: list[str]) -> str
open_review(paths: list[str]) -> str
get_review_status(session_id: str) -> str
```

See the tool docstrings for exact result shapes. Typical loop:

```text
record_baseline(["src/main.py", "src/new_file.py"])
(edit src/main.py; create src/new_file.py; run tests)
open_review(["src/main.py", "src/new_file.py"])
→ {"session_id": "a1b2c3d4e5f6", "url": "http://127.0.0.1:8417/s/a1b2c3d4e5f6", ...}
(show the URL to the user, continue working)
get_review_status("a1b2c3d4e5f6")
```

Rules:
- every path opened for review must have a baseline (error message names it);
- only UTF-8 text files are reviewable (binary files and directories are
  rejected with a clear error);
- review sessions are in-memory: `ALETHEIA_MAX_SESSIONS` (default 100) are
  kept, the oldest first dropped;
- the session id is the deterministic hash of the diff set — reopening the
  identical set of changes returns the same session.

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
| `ALETHEIA_PORT` | `8417` | port of the review web GUI (started when the first session opens) |
| `ALETHEIA_HOST` | `127.0.0.1` | bind host of the review web GUI (loopback only by default) |
| `ALETHEIA_MAX_SESSIONS` | `100` | in-memory review sessions kept (oldest dropped) |

## Development

```console
make install   # uv sync (Python 3.14)
make webui     # build the review GUI (npm + Vite) into the package
make check     # mypy + ruff
make test      # pytest
```

The web UI lives in `webui/` (Vite + React + TypeScript, CodeMirror 6 with
the merge view and `@codemirror/language-data` for syntax highlighting).
Its built output is committed to `src/aletheia_mcp/webui/dist` so the
published wheel ships the GUI without requiring Node at install time.

## License

MIT — see [LICENSE](LICENSE).
