# Components — aletheia

<!-- tags: components, modules -->

## `src/aletheia_mcp/main.py` — CLI entry point

- cyclopts `App` named `aletheia`; console script `aletheia = aletheia_mcp.main:app`.
- Default command `run()` starts the MCP server on stdio.
- `setup` subcommand: resolves the git root of the given directory (or
  `~/.vibe` with `--global`) and calls `setup.install_hook(base)`; prints where
  it installed.

## `src/aletheia_mcp/server/server.py` — MCP server core

- Builds `mcp = FastMCP("aletheia", instructions=...)` on import; the
  instructions string summarizes the review protocol for the agent.
- `run()` calls `mcp.run(transport="stdio")`. Importing the module starts no
  transport and no web server.

## `src/aletheia_mcp/server/tools/` — MCP tools

Importing the package registers the tools on `mcp` (see `server/__init__.py`).

- `review_tools.py` — the review protocol; each tool returns a compact JSON
  string and delegates to `get_service()`:
  - `record_baseline(paths)` — snapshot pre-edit content; starts the web
    server on first use; returns `{"url", "recorded", "marked_for_creation"}`.
  - `get_change_status()` — live drift poll; returns
    `{"url", "files_in_baseline", "files": [{path, kind, changed}]}`.
  - `remove_from_baseline(paths)` — approve: adopt working dir, drop entries.
  - `rollback_to_baseline(paths)` — reject: restore baseline on disk (delete
    creation-marked files), drop entries.
  - `edit(file_path, old_string, new_string, replace_all=False)` — the
    baseline-aware replacement for the built-in `edit` **and** `write_file`
    tools; returns `{"file", "message", "created", "baseline_registered",
    "url", ...}`.
- `system.py` — `ping()` returns `"pong"`.

## `src/aletheia_mcp/review/service.py` — `ReviewService`

The seam between transports and the review core; never imports transport code
beyond the lazy web-server starter. One process-wide instance via
`get_service()` / `set_service()` (tests use `set_service` for isolation).
Holds `settings`, `baselines` (a `BaselineStore`), the immutable
`trusted_root`, and a lock. Methods: `record_baseline`, `get_change_status`,
`remove_from_baseline`, `rollback_to_baseline` (prechecks all entries before
touching disk), `write_file_content` (GUI save-edit; only baseline files),
`edit_file`, `review_payload` (full contents + unified diffs for the GUI).

## `src/aletheia_mcp/review/baselines.py` — baseline store

- `Baseline` frozen dataclass: `content: str | None`; `None` is a creation
  marker (file planned to be created; reject deletes it).
- `read_text_or_none(path)` — UTF-8 read; `None` when missing; raises
  `UnsupportedFileError` for directories and non-UTF-8.
- `BaselineStore` — thread-safe `dict[Path, Baseline]`; `record` (missing
  files become creation markers; re-recording overwrites = new round), `get`,
  `remove` (all paths must be present), `paths` (sorted snapshot), `len`,
  `clear`.

## `src/aletheia_mcp/review/diffs.py` — diffs

- `unified_diff(old, new, label)` via `difflib`, with stable literal edge
  markers `<created>` / `<deleted>` when a side is absent (`None`).
- `canonical_diff_text(old, new, path)` — per-file line of the canonical text
  that session ids hash (`path\0diff`).
- `has_text_change(old, new)` — boolean drift check for status payloads.

## `src/aletheia_mcp/review/disk.py` — atomic disk effects

The only module that writes or deletes files. `write_text` writes a temp file
(prefix `.aletheia-`) in the target's parent directory and `os.replace`s it;
parent directories are never created. `delete` unlinks if present.

## `src/aletheia_mcp/review/editing.py` — the `edit` tool core

- `trusted_root(working_dir)` — git root of the CWD, falling back to the CWD;
  computed once per process in `ReviewService.__init__`.
- `contains(root, path)` — post-resolution containment check (defeats `..`,
  absolute-outside, and symlink escapes alike).
- `apply_edit(root, store, file_path, old_string, new_string, replace_all)` —
  evaluation order: trusted-root check → read/validate → baseline registration
  (only if absent) → atomic write. Existing file: exact-string replace,
  unique unless `replace_all`, `new_string != old_string`. Missing file with
  `old_string=""`: creation with full content (non-empty); parent must exist.
  On write failure a freshly registered baseline entry is removed again.

## `src/aletheia_mcp/web/app.py` — Starlette app

- Routes: `GET /` → redirect to `/review`; `GET /review` → the committed
  `webui/dist/index.html` (or an HTML fallback page if the bundle is missing);
  `GET /api/review`; `POST`/`DELETE /api/baseline/files`;
  `POST /api/rollback`; `POST /api/content`; static mount `/assets`.
- `LoopbackGuard` middleware: mutating `/api/*` requests must be
  `application/json` and, if they carry Origin/Referer, loopback-only.
- Errors map by domain type (`NotInBaselineError`→404,
  `InvalidDecisionError`→400, disk errors→500) with the message in `{"error"}`.
- The API acts only on paths present in the baseline.

## `src/aletheia_mcp/web/server.py` — lazy loopback server

`ensure_running(settings)` binds uvicorn on `settings.host`, port 0, in a
daemon thread, waits (up to 10 s) for the socket, and returns the constant
URL `http://{host}:{port}/review`. Idempotent; raises `ServerStartError` on
failure.

## `src/aletheia_mcp/settings.py`, `errors.py`, `setup.py`

- `settings.py` — pydantic-settings `Settings` with `env_prefix="ALETHEIA_"`;
  only `host` (default `127.0.0.1`). Port is autodetected, so no port setting.
- `errors.py` — `AletheiaError` base plus `UnsupportedFileError`,
  `NotInBaselineError`, `InvalidDecisionError`, `DiskEffectError`,
  `OutsideTrustedRootError`, `EditFailedError`, `ServerStartError`.
- `setup.py` — `git_root(directory)` via `git rev-parse --show-toplevel`;
  `install_hook(base_dir)` merge-safe/idempotent install of the
  `aletheia-baseline` post-tool hook into `.vibe/hooks.toml` plus the
  standalone `.vibe/hooks/aletheia_baseline.py` script.

## `webui/` — the review GUI (sources)

Vite + React 18 + TypeScript; CodeMirror 6 merge view (`@codemirror/merge`)
for the side-by-side diff.

- `src/App.tsx` — page shell: file list with kind badges, per-file
  Approve/Reject/Save edit and Approve all/Reject all, polling refresh that
  preserves unsaved drafts across live updates.
- `src/DiffPane.tsx` — the CodeMirror merge-view pane; `onEdit` reports drafts.
- `src/api.ts` — typed client for the JSON API (`fetchReview`,
  `addToBaseline`, `removeFromBaseline`, `rollback`, `saveContent`).
- `src/main.tsx`, `src/styles.css`, `index.html`, `vite.config.ts`,
  `tsconfig.json`, `package.json`/`package-lock.json`.
- Built output goes to `webui/dist` and is copied by `make webui` into
  `src/aletheia_mcp/webui/dist` (committed), with license sidecars from
  `webui/dist-sidecar/`.

## `tests/`

- `tests/conftest.py` — `service` fixture: fresh `ReviewService` per test
  rooted at `tmp_path`, web server stubbed to a fixed URL, `set_service`.
- `tests/unit/` — one module per unit: baselines, diffs, disk, editing,
  service, settings, setup (hook merge/idempotency + hook script over
  synthetic payloads), review tools, web API, main CLI.
- `tests/integration/test_e2e.py` — real FastMCP client + real loopback HTTP
  server + real disk: record → edit → live diff → user edit+approve → reject
  of a created file; asserts URL stability. Loopback only, never the network.

## `.agents/planning/aletheia/` — PDD artifacts

Design docs and implementation plan (`rough-idea.md`, `idea-honing.md`,
`summary.md`, review revisions, `design/`, `implementation/`, `research/`).
Governed by the repo-root PDD skill; see `CONTRIBUTING.md`.
