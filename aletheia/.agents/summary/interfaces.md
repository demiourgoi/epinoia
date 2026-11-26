# Interfaces — aletheia

<!-- tags: interfaces, api, protocol -->

Aletheia exposes four external interfaces: the MCP tool protocol (agent),
the HTTP JSON API + GUI page (browser), the Vibe hook (post-tool coaching),
and the CLI. All review operations return compact JSON strings/objects.

## 1. MCP tool protocol (stdio)

<!-- tags: mcp, tools -->

Server name `aletheia`; hosts prefix tool names (Vibe exposes them as
`aletheia_record_baseline`, `aletheia_edit`, …). The `mcp` instructions string
in `server/server.py` summarizes the protocol to the agent.

| Tool | Signature | Returns (JSON) |
| --- | --- | --- |
| `record_baseline` | `paths: list[str]` | `{"url", "recorded": [...], "marked_for_creation": [...]}` — starts the web server on first use |
| `get_change_status` | `()` | `{"url", "files_in_baseline": int, "files": [{"path", "kind": "created"\|"deleted"\|"modified", "changed": bool}]}` — never blocks |
| `remove_from_baseline` | `paths: list[str]` | `{"removed": [...], "files_in_baseline": int}` — approve/adopt |
| `rollback_to_baseline` | `paths: list[str]` | `{"rolled_back": [...], "files_in_baseline": int}` — reject/restore on disk |
| `edit` | `file_path: str, old_string: str, new_string: str, replace_all: bool = False` | `{"file", "message", "created": bool, "baseline_registered": bool, "url"}` plus `old_string`/`new_string` for edits |
| `ping` | `()` | `"pong"` |

Protocol rules (also in the tool docstrings, which are the agent's manual):

- Record a file **before** editing it; re-record after a decision to anchor a
  new round. Error messages name the offending path.
- Paths may be absolute or working-directory relative; they are resolved and
  deduped (`_resolve_all`).
- Only UTF-8 text files are reviewable; binaries and directories are rejected
  with `UnsupportedFileError`.
- `edit` semantics: existing file → exact `old_string`→`new_string`, unique
  match unless `replace_all=true`, `new_string` must differ; missing file →
  pass `old_string=""` and the full content as `new_string` (creation;
  `replace_all` ignored; parent directory must exist). The pre-change state is
  registered in the baseline automatically on first change (created files get
  a creation marker). `file_path` is confined to the trusted root after
  symlink resolution.

## 2. HTTP API + review page (loopback)

<!-- tags: http, api -->

Base URL returned by the tools, constant per process:
`http://{ALETHEIA_HOST}:{free-port}/review` (default host `127.0.0.1`).

| Method & path | Body | Effect / response |
| --- | --- | --- |
| `GET /` | — | 307 redirect to `/review` |
| `GET /review` | — | the GUI (`webui/dist/index.html`), or an HTML fallback if the bundle is missing |
| `GET /assets/*` | — | static GUI assets (mounted only when present) |
| `GET /api/review` | — | `{"url", "files": [{"path", "kind", "changed", "baseline": str\|null, "current": str\|null, "diff": str}]}` — full live payload |
| `POST /api/baseline/files` | `{"paths": [str, ...]}` (non-empty) | record baselines → `{"url", "recorded", "marked_for_creation"}` |
| `DELETE /api/baseline/files` | `{"paths": [...]}` | approve → `{"removed", "files_in_baseline"}` |
| `POST /api/rollback` | `{"paths": [...]}` | reject → `{"rolled_back", "files_in_baseline"}` |
| `POST /api/content` | `{"path": str, "content": str}` | GUI save-edit; only for baseline files → `{"path", "written": true}` |

Guard (`LoopbackGuard`): mutating `/api/*` (POST/DELETE) requests must have
`Content-Type: application/json` and, when Origin/Referer is present, a
loopback host (`127.0.0.1`, `::1`, `localhost`, or the request host) —
otherwise 403. Errors return `{"error": str}` with status 400
(`InvalidDecisionError`), 404 (`NotInBaselineError`), 500 (disk/server).

## 3. Vibe hook (installed by `aletheia setup`)

<!-- tags: vibe, hook -->

- `aletheia setup [directory] [--global]` writes, under the **git repository
  root** of the directory (or `~/.vibe` with `--global`):
  - `.vibe/hooks.toml` — appends a `[[hooks]]` block named `aletheia-baseline`
    (`type = "post_tool"`, `match = "re:edit|write_file"`,
    `command = "python .vibe/hooks/aletheia_baseline.py"`); merge-safe and
    idempotent (keyed on the hook name).
  - `.vibe/hooks/aletheia_baseline.py` — reads the post_tool payload from
    stdin; on a successful edit/write tool call whose input names a file, it
    prints `{"hook_specific_output": {"additional_context": "Aletheia: ...
    call record_baseline ..."}}`. Best-effort: it runs in its own process and
    cannot inspect the server's in-memory baseline.
- Recommended primary enforcement is instead disabling the host's built-in
  `edit`/`write_file` tools (`disabled_tools = ["edit", "write_file"]`) so all
  changes flow through `aletheia_edit`.

## 4. CLI

<!-- tags: cli -->

- `aletheia` (default) — run the MCP server on stdio.
- `aletheia setup [directory] [--global]` — install the hook (above); prints
  the `hooks.toml` path and notes when it installs at the git root rather than
  the given directory.
- `aletheia --version` / `--help` via cyclopts.

## 5. Configuration

<!-- tags: config, env -->

| Env var | Default | Meaning |
| --- | --- | --- |
| `ALETHEIA_HOST` | `127.0.0.1` | Bind host of the review web server (loopback by default) |

No port setting exists: the port is OS-assigned (bind port 0) and the URL is
returned by the tools.
