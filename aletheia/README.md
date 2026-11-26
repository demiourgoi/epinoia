# Aletheia

**Aletheia** (ἀλήθεια: unconcealment) is an MCP server that gives terminal
coding agents (such as Mistral Vibe CLI) the Zed-style **asynchronous
change review** workflow: the agent records a baseline before editing, you
review the live diff in a local web GUI, and approve or reject per file —
without ever blocking the conversation.

1. Before editing, the agent says which files it is about to change; Aletheia
   snapshots them and opens a review page whose URL is stable for the session.
2. The agent **edits the files normally**. Changes are on disk, so linters
   and tests see them; the review page always shows the [live diff](#live-review).
3. You open the URL: a compact **side-by-side diff** per file. **Approve**
   (keep the change), **edit** then approve, or **reject** (restore the
   original content) — per file or all at once.
4. A file is under review only until you decide on it. If the agent changes
   it again later, a new review round starts.

```mermaid
sequenceDiagram
    participant U as User
    participant A as CLI agent
    participant M as Aletheia MCP (stdio)
    participant W as Review GUI (loopback HTTP / free port)
    A->>M: record_baseline(files) starts W, returns URL
    A->>A: edits files on disk, runs linters
    A->>U: shows the constant URL
    U->>W: reviews live highlighted diffs
    U->>W: approve (adopt) / edit+save / reject (rollback)
    W->>W: rejected files restored on disk, out of review
    A->>M: get_change_status()
    M-->>A: live drift, decided files gone from the baseline
```

## Live review

The review page compares each file's pre-edit snapshot with its current
content, so it never goes stale: you can run linters and tests while the
diff updates. Only UTF-8 text files can be reviewed; binaries and
directories are reported as unsupported. The review server listens on
loopback only and lives as long as the agent session.

## Screenshots

| Java file under review | Python file under review |
| --- | --- |
| ![Java diff with red/green changed chunks](docs/screenshots/review-diff-java.png) | ![Python diff with red/green changed chunks](docs/screenshots/review-diff-python.png) |

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `ALETHEIA_HOST` | `127.0.0.1` | bind host of the review web GUI (loopback only by default) |

No port needs configuring: the review server picks a free port and the URL
it reports is the one to open.

## Mistral Vibe setup

Follow these three steps to use Aletheia with the Vibe CLI. Background:
[Vibe configuration reference](https://docs.mistral.ai/vibe/code/cli/configuration-reference)
and [MCP servers docs](https://docs.mistral.ai/vibe/code/cli/mcp-servers).

### 1. Register the MCP server

Append one `[[mcp_servers]]` block to `~/.vibe/config.toml` (user level) or
`./.vibe/config.toml` at the repository root (project level). Append it
rather than replacing existing blocks, and create the file if needed. Set
`command` to the absolute path of your `aletheia` executable:

```toml
# https://docs.mistral.ai/vibe/code/cli/mcp-servers
[[mcp_servers]]
name = "aletheia"
transport = "stdio"
command = "/home/you/path/to/epinoia/aletheia/.venv/bin/aletheia"
args = []
env = { }
```

If you installed from PyPI, use `uvx` instead:

```toml
command = "uvx"
args = ["--from", "aletheia", "aletheia"]
```

### 2. Forbid the built-in edit and write_file tools (recommended)

Aletheia's baseline-aware **`edit`** tool replaces Vibe's **built-in `edit`
and `write_file` together**: it edits existing files (exact `old_string` →
`new_string` replacement) and creates new ones from scratch (`old_string`
empty, `new_string` the full content). Every change through it records the
review baseline automatically in the same call — an edit made this way
**cannot** skip the baseline, so nothing you would want to review goes
unreviewed.

Making it the only path is what actually enforces that, and it is more
effective than the reminder hook of step 3: the hook only *nudges* the
agent after an edit already happened (best-effort coaching that cannot
inspect the baseline), while disabling the built-ins leaves the agent no
way to change a file except through Aletheia. Forbid both built-ins in the
same `config.toml`:

```toml
disabled_tools = ["edit", "write_file"]
# or, equivalently:
[tools.edit]
permission = "never"
[tools.write_file]
permission = "never"
```

Vibe prefixes MCP tools with the server name, so Aletheia's tool appears
as `aletheia_edit` and is not affected by `disabled_tools`. These keys also
work in a custom agent file (`.vibe/agents/<name>.toml`) to scope the
restriction to one agent.

"Force edits through Aletheia" is not strictly required — the agent can
also call `record_baseline` by hand before editing with its own tools —
but it is the reliable setup and the one this README recommends.

### 3. Optionally install the reminder hook (fallback)

The hook still earns its keep for the change channels step 2 cannot close
(shell commands, other MCP servers): it nudges the agent to record files
after it edits them by other means, so reviews are not missed:

```console
aletheia setup            # project-level (this repository)
aletheia setup --global   # user-level (~/.vibe/)
```

Run `aletheia setup` from inside the project you want to protect; it
reports where it installed the hook. The hook is best-effort coaching, so
keep step 2 as the primary mechanism.

## Using Aletheia with other MCP hosts

Any MCP host that supports stdio can launch Aletheia the same way:

```json
{
  "mcpServers": {
    "aletheia": { "command": "uvx", "args": ["--from", "aletheia", "aletheia"] }
  }
}
```

## Development

Building, testing, architecture, and contribution notes live in
[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).

## License

MIT — see [LICENSE](LICENSE).
