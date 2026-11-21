# Implementation plan: Aletheia

- [x] Step 1: Project skeleton runnable as `aletheia` on Python 3.14
- [x] Step 2: Review core — baselines, sessions, diffs, disk effects
- [x] Step 3: MCP tools — record_baseline, open_review, get_review_status
- [ ] Step 4: Loopback web server, JSON API, React diff GUI
- [ ] Step 5: Packaging parity, README, end-to-end verification

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

_(to be filled on completion)_

## Step 5 — Implementation notes

_(to be filled on completion)_

## Reviews per step

_(each step's commit is reviewed per the ponytail-review skill before the
next step starts; review files are `implementation/step-{I}-review-rev{J}.md`)_

Each step's commit got a ponytail review (see
`implementation/step-{I}-review-rev{J}.md`, plus a `final-pdd-review` in
`../summary-review-rev1.md`). All step reviews shipped on round 1 except
Step 4 (round 2), and the final review shipped on round 1, staying within
the 3-round cap.
