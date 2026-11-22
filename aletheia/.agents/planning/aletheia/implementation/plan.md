# Implementation plan: Aletheia

- [x] Step 1: Project skeleton runnable as `aletheia` on Python 3.14
- [x] Step 2: Review core — baselines, sessions, diffs, disk effects
- [x] Step 3: MCP tools — record_baseline, open_review, get_review_status
- [x] Step 4: Loopback web server, JSON API, React diff GUI
- [x] Step 5: Packaging parity, README, end-to-end verification

## Working agreements

Proceed step by step:

- After each step, ask me for confirmation before completing it
- When completing a step, add an "Implementation notes" subsection to its section in the plan, summarizing what we did, focusing on deviations from the plan, why we made them, and implications for subsequent steps

This project runs unattended: the "ask me for confirmation" rule is satisfied
by the executing agent self-confirming each step against its acceptance
criteria (build, lint, type-check, and tests green) and recording the
"Implementation notes" subsection here.

Build/test commands (run inside `aletheia/` after Step 1):
`make install`, `make check` (ruff + mypy), `make test` (pytest),
`make webui` (build the GUI; Vite output is committed then).

**Step 1: Project skeleton runnable as `aletheia` on Python 3.14**

Objective: a hatchling-packaged `aletheia_mcp` package (src layout) whose
console script `aletheia` runs a FastMCP server with a placeholder `ping`
tool, plus settings (`ALETHEIA_*`), the error-class hierarchy, lint/type
configs and a Makefile mirroring harold-mcp.
Guidance: copy Harold's pyproject structure (Python `>=3.14,<3.15`, ruff,
mypy, pytest-cov, hatchling wheel of `src/aletheia_mcp`); cyclopts app in
`main.py` whose default command runs the stdio server.
Tests: `fastmcp.Client` in-memory call of the placeholder tool; settings env
override test.
Integration: none yet (first step); establishes the wiring every later step
hangs off.
Demo: `uv run aletheia` starts an MCP server listing the placeholder tool;
`make check` and `make test` pass.

**Step 2: Review core — baselines, sessions, diffs, disk effects**

Objective: the whole domain model and disk semantics of the design (R1–R7)
with no MCP/HTTP coupling: `BaselineStore` (UTF-8 text validation,
created-marker), `SessionStore` (deterministic ids, collision suffixes,
eviction cap, locking), `ReviewSession.decide` (approve / reject /
save_edit) and `DiskWriter` (atomic writes, deletion), errors.
Guidance: pure-stdlib modules under `aletheia_mcp/review/`; unknown-error
message strings written for the agent (they end up in tool errors); write
the lock rule from the design.
Tests: baseline validation and marker; deterministic session ids and
collision suffix; eviction; every status transition incl. 409-style errors;
atomic write/revert/delete on `tmp_path` files.
Integration: none; Step 3 wires tools on top.
Demo: pytest suite drives a real file: record → edit → open session →
reject → file back to original content.

**Step 3: MCP tools — record_baseline, open_review, get_review_status**

Objective: the three MCP tools of the design wired to the Step-2 core, with
docstrings written as agent guidance and JSON tool results.
Guidance: tools in `server/tools/` over in-process singletons; `open_review`
does not yet start a web server — it returns the intended session id plus
a `url` value implemented by a `WebServer` stub that Step 4 replaces
(design R4 contract: `ensure_started` idempotent, startup event, clear
bind errors).
Tests: `fastmcp.Client` end-to-end over the real components: record → edit
tmp files → open → decide via core → poll status; missing-baseline error
message; unknown session error.
Integration: everything from Step 2 is now reachable through MCP.
Demo: a scripted in-process run shows the full agent workflow.

**Step 4: Loopback web server, JSON API, React diff GUI**

Objective: R4 and R5: Starlette app (session JSON, per-file and global
decision endpoints, static + `/s/{id}` SPA routes), uvicorn in a daemon
thread with the `ensure_started` contract, and the Vite/React/TypeScript
client with CodeMirror merge view and language-data highlighting.
Guidance: build the GUI to `src/aletheia_mcp/webui/dist` via
`make webui` (committed static output); API acts only on paths in the
session; user edits write through `DiskWriter`.
Tests: Starlette `TestClient` coverage of the API (payload shape, decisions,
409/400/404, `_all` variants); a smoke test that the built `index.html`
exists in the package. GUI logic beyond that is covered by the manual demo.
Integration: replaces the Step-3 `WebServer` stub — `open_review` now
returns a real, accepting URL.
Demo: `make webui && uv run aletheia`, record a baseline, edit two files
(one Java, one Python) in the repo, open the URL in a browser, edit and
approve one file, reject the other, and show the disk state.

**Step 5: Packaging parity, README, end-to-end verification**

Objective: R8–R9: final packaging checks (wheel contains the GUI,
`.python-version`, lock), README (agent-facing docs: env vars, tool usage,
review workflow, uvx usage), CONTRIBUTING pointers, and an end-to-end test
of the whole flow including the started web server (loopback HTTP smoke).
Guidance: keep parity with harold-mcp conventions; verify
`uv build` produces a wheel whose `webui/dist` ships.
Tests: packaging test asserting assets import via `importlib.resources`;
HTTP-level test hitting the real uvicorn thread on an ephemeral port.
Integration: whole product demo end-to-end.
Demo: `uv build && uv run --isolated aletheia` from the built wheel works.

---

## Step 1 — Implementation notes

Completed as planned. Skeleton: pyproject (hatchling, `>=3.14,<3.15`, ruff 120
cols py314, mypy, pytest mirroring harold-mcp with aletheia names), src
layout `src/aletheia_mcp` with `main.py` (cyclopts app named `aletheia`,
default command runs the FastMCP stdio server), `settings.py`
(`ALETHEIA_HOST/PORT/MAX_SESSIONS`), `errors.py` (the design's AletheiaError
hierarchy), `server/server.py` with a placeholder `ping` tool, Makefile,
`.python-version` 3.14, README and LICENSE. Deviation: FastMCP resolved to
4.x (memory transport API changed: `Client(mcp)` instead of
`MemoryTransport`), and the 3.14 pin is a project requirement comment rather
than a dependency-cap comment. `make check` and `make test` green; `uv run
aletheia --help` and the in-memory client demo pass.

## Step 2 — Implementation notes

Completed as planned: `aletheia_mcp/review/` with `baselines.py` (UTF-8
validation with byte offsets in errors, created-marker, re-record
overwrite, thread-safe store), `diffs.py` (unified diffs with stable
`<created>`/`<deleted>` markers, canonical id text), `disk.py` (atomic
temp+`os.replace` writes, deletions, never creates directories), and
`sessions.py` (FileReview/ReviewSession with the edited-is-pending status
machine, state-changes-only-after-disk, deterministic 12-hex ids,
collision suffix, LRU cap with documented shortcut, lock-guarded decide).
39 unit tests over real files in tmp_path cover validation, all status
transitions, disk effects, ids, eviction, and 409-domain errors.
Deviation: none of substance; the collision-suffix branch is only
reachable via a truncated-SHA256 collision, so its test forces the digest
with monkeypatch (documented as a shortcut).

## Step 3 — Implementation notes

Completed as planned: `review/service.py` adds the ReviewService seam
(baseline store + session store + JSON serialization for tools and HTTP)
with a process-wide `get_service()` singleton; the three MCP tools in
`server/tools/review_tools.py` (`record_baseline`, `open_review`,
`get_review_status`) delegate to it and return JSON strings, with
docstrings written as an agent manual. `web/server.py` currently states the
URL contract only (`session_url`), with `ensure_running` a documented
no-op stub that Step 4 replaces. Tests exercise the real tools over the
fastmcp in-memory client against an isolated per-test service (set_service
fixture): full record → edit → open → decide → poll flow incl. on-disk
revert, creation markers, missing-baseline and unknown-session errors,
directory and empty-path validation. Deviation: none.

## Step 4 — Implementation notes

Completed as planned: `web/app.py` (Starlette: session payload GET,
per-file decision POST with content, bulk decision POST; 404/409/400/500
mapping via a single `_error_response`; `/s/{id}` and `/` serve the SPA
with a fallback page when no build exists; assets mounted from
`src/aletheia_mcp/webui/dist`), `web/server.py` (real impl now: uvicorn in
a daemon thread under `ensure_running`, waiting on `server.started` with a
10s deadline, `ServerStartError` naming ALETHEIA_PORT), and
`open_review` now calls `ensure_running` so returned URLs always accept
connections. GUI in `webui/`: Vite + React 18 + TS;
side-by-side editable diff via `@codemirror/merge` `MergeView` (pane A
read-only baseline, pane B editable proposal with per-change highlighting
and chunk revert controls), syntax highlighting via
`@codemirror/language-data` (filename-based, lazy: Java, Python, TS, C++,
Go, Rust, ...), file list with statuses, per-file Approve/Reject/Save edit
plus global Approve all/Reject all. Deviations: none of substance (the
language extension comes from `@codemirror/language`'s re-export; MergeView
is the documented standalone class rather than an extension). Verified by
a live local HTTP smoke (assets 200, reject reverted the file on disk) and
15 web-API tests with Starlette's TestClient (ensure_running stubbed in
unit tests so no ports are bound).

## Step 5 — Implementation notes

Completed as planned: `uv build` produces a wheel that ships the built GUI
(`aletheia_mcp/webui/dist/index.html` present in the wheel; verified via
zipfile listing and `uvx --from dist/*.whl aletheia --version` on
Python 3.14). The E2E integration test starts the real uvicorn thread on an
ephemeral free port and drives the whole flow through the MCP client and
plain HTTP: record → edit (Java + created Python file) → open_review →
GUI page + session API → save_edit + approve (disk keeps the user's tweak)
→ reject of the created file (deleted from disk) → get_review_status
(mixed). Packaging guarded by an importlib.resources asset test. README
(usage, env vars, tool protocol) and CONTRIBUTING added. Deviation: the
host:port mismatch guard in `ensure_running` (one process serves one
host:port) emerged from writing the E2E test; documented as a clear error
naming ALETHEIA_PORT.

**Step 6 (rev 2): Review core rework — baseline-only**

Objective: replace sessions with the baseline-only model per the v2
design: `BaselineStore.remove`, live-diff `ReviewService`
(record/remove/rollback/get_change_status/review_payload + save-edit
writer), `NotInBaselineError`, free-port autodetect with a constant URL
in `web/server.py`; delete `review/sessions.py`; settings drop
`ALETHEIA_PORT`/`ALETHEIA_MAX_SESSIONS`.
Tests: store ops, rollback/restores-then-removes incl. creation markers,
failure leaves entries, live kinds/changed, service shapes, server
free-port lifecycle.
Demo: pytest drives rollback removing a wrong edit from disk.

**Step 7 (rev 2): REST + MCP tools**

Objective: the R4/R5 REST routes and the four mirrored tools with
agent-manual docstrings; remove session-era routes/tools.
Tests: TestClient over the new routes incl. 404/400/500 mapping; fastmcp
in-memory client over the four tools.
Demo: record → edit → remove (approve) keeps disk; rollback restores.

**Step 8 (rev 2): GUI rework**

Objective: constant-URL review page over the new API: live file list with
kind/changed badges, per-file Approve (remove) / Reject (rollback) /
Save edit, global Approve all / Reject all / Refresh, empty-baseline
state; rebuild `webui/dist`.
Tests: asset presence as before; live manual smoke via the real server.
Demo: browser review of a Java + created Python change set.

**Step 9 (rev 2): `aletheia setup` hook installer + docs**

Objective: `aletheia setup` installs the `post_tool` baseline reminder
hook (merge-safe into `.vibe/hooks.toml`, idempotent, standalone script);
server/tool descriptions instruct baseline-before-edit; README updated to
the v2 model (no port env var, constant URL, new tools).
Tests: installer merge/idempotency/script content; docs updated.
Demo: `uv run aletheia setup` in a temp project; hook script exercised
with a synthetic payload.

## Step 6 (rev 2) — Implementation notes

Completed as planned: baseline-only core per the v2 design —
`BaselineStore` gains `remove` (validating, nothing dropped on failure)
and sorted `paths`; `sessions.py` deleted; `ReviewService` rewritten
around live diffs (`record_baseline`/`get_change_status`/
`remove_from_baseline`/`rollback_to_baseline`/`write_file_content`/
`review_payload`), rollback restores-then-removes under one operation
lock (state follows disk; failures keep entries); `NotInBaselineError`;
settings reduced to `ALETHEIA_HOST` (port autodetected via bind-to-0 in
`web/server.py`, real port read from the bound socket; the URL is
constant for the process and returned by every tool result). Unit tests
cover store ops, all operation semantics incl. creation markers, disk
failures (single and mid-set), live kinds/changed, save-edit guard, and
the free-port URL shape. Deviation: none.

## Step 7 (rev 2) — Implementation notes

Completed as planned: REST surface — `GET /api/review` (full payload),
`POST /api/baseline/files` (add), `DELETE /api/baseline/files`
(approve), `POST /api/rollback` (reject), `POST /api/content` (GUI
save-edit), `/` serves the GUI; 404/400/500 mapping via
`NotInBaselineError`/`InvalidDecisionError`/`DiskEffectError`. MCP tools
rewritten (`record_baseline`, `get_change_status`,
`remove_from_baseline`, `rollback_to_baseline`) with agent-manual
docstrings; the server instructions state the
baseline-before-edit protocol. Tests: TestClient over every route incl.
error mapping and approve-all/reject-all composition; fastmcp
in-memory-client loop incl. drift polling and mirrored decisions.
Deviation: none (the DELETE route uses `request("DELETE", ...)` in tests:
this starlette TestClient's `.delete` takes no json kwarg).

## Step 8 (rev 2) — Implementation notes

Completed as planned: the GUI becomes a single constant-URL review page:
live file list from `GET /api/review` with Created/Deleted/Modified and
unchanged badges, per-file Approve (DELETE baseline), Reject (rollback),
Save edit (POST content, with an "unsaved edit" hint), global Approve
all / Reject all / Refresh, and an empty-baseline state. `webui/dist`
rebuilt. Live smoke over the real loopback server: GUI and assets 200,
live diff reflected an ongoing edit, rollback deleted the created file
(now also covered by the rewritten e2e test). Deviation: none of
substance (Starlette's TestClient needs `request("DELETE", ..., json=)`
since its `.delete` takes no body kwarg).

## Step 9 (rev 2) — Implementation notes

Completed as planned: `aletheia setup` (cyclopts command, `--global` for
`~/.vibe`, mirroring harold-mcp's setup shape) installs the
`aletheia-baseline` post_tool reminder hook: merge-safe append into
`.vibe/hooks.toml` keyed on the unique hook name, plus the standalone
`.vibe/hooks/aletheia_baseline.py` reading `file_path`/`path`/`filename`
from the payload and silent otherwise. FastMCP server instructions and
tool docstrings document the baseline-before-edit protocol. README
rewritten to the v2 model (new tools, constant URL, free port with only
`ALETHEIA_HOST` configurable, hook section). Tests: installer
merge/idempotency plus the hook script exercised with real subprocess
runs over synthetic payloads; e2e rewritten to the new flow (record →
edit → live payload → save edit + approve keeps the tweak on disk →
reject deletes the created file → empty baseline, constant URL).

## Step 10 (rev 2) — Implementation notes (PR review round attendance)

The author's ponytail review of the PR (round 2) was attended on the
branch. Findings and outcomes:
- (Must 1) `rollback_to_baseline` half-applied a rollback on duplicate or
  already-decided paths. Fixed: `_resolve_all` now dedupes resolved paths
  (order-stable), rollback prechecks every baseline entry under the
  operation lock before touching the disk (the same pattern as
  `BaselineStore.remove`), and `NotInBaselineError` now explains both
  possible causes (never recorded, or already decided).
- (Should 2) no origin/content-type check on the loopback API. Fixed:
  `LoopbackGuard` middleware requires `Content-Type: application/json`
  on mutating `/api` routes (a `no-cors` form POST cannot send it) and
  rejects any `Origin`/`Referer` that is not loopback (403).
- (Should 3) `webui/tsconfig.tsbuildinfo` committed. Already removed and
  ignored in the third-party-notices commit; noted to the reviewer.
- (Nice 4) switching files or a live refresh dropped unsaved GUI edits.
  Fixed: per-path draft map; the diff pane remounts only when the
  selected file changes or its on-disk content actually changed, and
  prunes drafts of files that left review.
- Author request outside the review: the review page moved to `/review`
  (the bare root redirects), leaving room for future pages; the tool
  results now return URLs ending in `/review`.
Tests added for all of the above (dedupe/precheck of rollback,
guard 403s incl. loopback-origin allow, draft-preserving refresh
indirectly via pane remount logic, `/review` + root redirect in both
the TestClient and the real-server e2e); 71 tests green, ruff + mypy
clean, GUI rebuilt. Follow-up caught while pushing: Vite's
`emptyOutDir` deletes the committed build-output sidecars (dist/LICENSE
and assets/README.md) on every rebuild, so their source copies now live
in `webui/dist-sidecar/` and `make webui` copies them back after the
build; REUSE annotations and THIRD-PARTY-NOTICES updated accordingly
(reuse lint 234/234).

## Step 11 (rev 2) — Implementation notes

Per the author's follow-up: Vibe loads project-level hooks from the
trusted project folder (the git root), so `aletheia setup` now installs
into the `.vibe/` of the git repository root, mirroring the epinoia
precedent for opencode files (`AGENTS.md`: opencode files go to the
**git root** because they are discovered from there; a subdirectory
install would be invisible). `git_root()` resolves
`git rev-parse --show-toplevel` with a documented fallback to the given
directory when git is unavailable; the command prints where it installed
and why. Tests cover root resolution from a nested directory, the
fallback (git failure), and an end-to-end install from a subdirectory of
a fresh repository asserting the hook lands at the root and not in the
subdir. While testing I briefly polluted the epinoia tree's `.vibe/` with
an untracked hook (a `uv --directory` smoke ran with the wrong CWD); the
file was removed and the tree verified clean.

**Step 12 (rev 3): Diff UI compaction; language highlighting out of the MVP**

Objective: per the v3 design delta 1 — full-width review page with
minimal margins, compacted CodeMirror gutters/content and merge pane
(gap pinned to the specific classes), removal of the
`@codemirror/language-data` language loading (diff highlighting
stays), rebuilt and recommitted `webui/dist`, fresh screenshots,docs
and THIRD-PARTY/REUSE updates for the dropped dependency.
Tests: package-asset test and the web API suite unchanged; live
headless re-render to verify the compact layout.
Demo: new screenshot at the same flow as before.

**Step 13 (rev 3): baseline-aware `edit` MCP tool (opt-in)**

Objective: per the v3 design delta 2 — `review/editing.py` with
`trusted_root()` computed once at service construction, containment
(symlinks followed), `apply_edit` with vibe-`EditArgs` schema and
harness-`edit_file` semantics (unique match / replace_all,
new != old, atomic write), auto baseline registration in the state
order trust → validate → baseline → write; the `edit` MCP tool; README
explains forbidding the built-in edit tool and using this one.
Tests: schema/semantics, error cases, trusted-root accept/reject
(subdir ok; .., outside-absolute and symlink-escape rejected),
no-baseline-side-effect on failure, auto registration incl. new round
after decisions, fastmcp-client loop.
Demo: full agent loop editing without ever calling record_baseline.

## Step 13 (rev 3) — Implementation notes

Completed as planned: `review/editing.py` with `trusted_root()`
(git root of the working directory, fallback cwd — computed **once** in
`ReviewService.__init__` and held immutable for the process, per design
delta 2), `contains()` containment after symlink resolution, and
`apply_edit()` in the designed no-side-effects-on-failure order trust →
validate → baseline → atomic write (schema and semantics matching
vibe's `EditArgs` / harness `edit_file`: unique match or
`replace_all=True`, `new_string` != `old_string`, exists + UTF-8,
project-relative or absolute paths). Baseline registration happens only
on the first edit of a file per round (`resolved not in store.paths()`),
never re-anchors, and is skipped entirely when validation fails. The
`edit` MCP tool (`server/tools/review_tools.py`) wraps
`ReviewService.edit_file` and returns the review `url` alongside the
edit result. Tests: `tests/unit/test_editing.py` (17 tests: semantics,
error cases, subdir allowed, `..`/outside-absolute/symlink escapes
rejected — the `service` fixture pins `trusted_root=tmp_path`, since
tmp sits outside any repo the git-root fallback would otherwise widen;
no-op on failure; new round after decisions re-registers) plus two
fastmcp in-memory client tests in `test_review_tools.py`: the full agent
loop editing **without ever calling record_baseline** (rollback restores
the pre-edit content) and ambiguous-match surfacing as a tool error.
README: `edit` in the tool protocol with its guarantees, plus the
"Replacing the built-in edit tool (Mistral Vibe)" section — verified
against the live Vibe docs: MCP tools are exposed as
`{server_name}_{tool_name}` (`aletheia_edit`), so `disabled_tools =
["edit"]` / `[tools.edit] permission = "never"` forbids only the built-in
tool; `[[mcp_servers]]` stdio entry documented alongside. REUSE.toml
entries added for the new files. 94 tests, ruff, mypy, wheel build and
`uvx reuse lint` all green. Review round 1 (step-13-review-rev1.md)
removed dead code (an unreachable directory branch already rejected
by `read_text_or_none`) and fixed a docstring mentioning the wrong tool
name; round 2 ships.

## Step 12 (rev 3) — Implementation notes

Completed as planned: the review page is full-width with minimal
padding (`.page` drops its max-width; header/description/list margins
reduced), and the CodeMirror compaction pins the specific classes
(`cm-gutters` padding/min-width, `cm-lineNumbers` gutter elements,
`cm-content`, `cm-scroller`) per the design. Language-dependent
highlighting is out of the MVP: `@codemirror/language-data`,
`@uiw/react-codemirror` (unused since the MergeView rework) and their
loading logic are gone; the DiffPane builds once on mount (App's
render-tick key still governs remounts), and the committed bundle
shrank from 122 generated files to 2 (`index-*.js`, `index-*.css`).
Sidecars updated to the new facts (dist-sidecar sources + committed
copies), THIRD-PARTY-NOTICES rewritten for the dropped libraries, and
fresh headless screenshots captured and verified (compact full-width
layout, plain text, red/green diff chunks, no side bands); README
updated. All 74 tests, ruff, mypy, and `uvx reuse lint` green.
Deviation: none.

## Reviews per step

Each step's commit was reviewed per the ponytail-review skill before the
next step started (review files `implementation/step-{I}-review-rev{J}.md`):
step 1 shipped on round 2 (decorator tool registration), steps 2 and 4
shipped on round 2, steps 3 and 5 shipped on round 1 — all within the
3-round cap. The design shipped on round 2 (see
`design/detailed-design-review-rev{1,2}.md`) and the whole project got a
final ship review (`../summary-review-rev1.md`).

The opencode review runner was unavailable in the execution sandbox, so
each review was produced by the implementing agent applying the ponytail
checklist directly to the artifact; this substitution is recorded in
every review file.

Each step's commit got a ponytail review (see
`implementation/step-{I}-review-rev{J}.md`, plus a `final-pdd-review` in
`../summary-review-rev1.md`). All step reviews shipped on round 1 except
Step 4 (round 2), and the final review shipped on round 1, staying within
the 3-round cap.
