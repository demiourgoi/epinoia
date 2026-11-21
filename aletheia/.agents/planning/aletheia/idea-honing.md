# Idea honing

This task is executed fully unattended. The PDD skill requires interactive
question/answer refinement; the mandate for this project is that the agent
answers each question itself using the constraints in the rough idea plus best
judgement, and records the decision here. Each entry keeps the question as it
would have been asked, the considered alternatives, and the chosen answer.

---

## Q1: How does the server obtain the "before" content of a file if the agent's edits are already on disk?

**Alternatives considered:**
- Use git (diff against `HEAD`). Fragile: non‑git directories, dirty trees,
  unrelated edits, staged changes.
- Re‑derive from editor history — unavailable: the agent edits via shell tools.
- An explicit baseline snapshot tool the agent calls before editing.

**Chosen answer:** an explicit `record_baseline` MCP tool. Before editing, the
agent passes the list of files it plans to touch; the server stores their
current content in memory. Paths that don't exist yet are recorded as "new
file" markers so the agent can list files it will create. This keeps the
mechanism correct in and out of git, with no dependency on repository state.

## Q2: Is the review blocking for the agent?

**Chosen answer:** no. `open_review` returns a session id and URL immediately;
the agent keeps working (or shows the URL to the user) and can poll
`get_review_status`. There is no wait/tool-confirmation gate. This matches
Zed: edits are on disk and reviewable while the conversation continues.

## Q3: What does rejection do, exactly?

**Chosen answer:** rejecting a file writes the recorded baseline content back
to disk immediately (atomic write: temp file + `os.replace`). A baseline whose
marker is "new file" deletes the file on rejection. "Reject all" applies this
to every pending file. Approval leaves the file as it is on disk; when the user
edits in the GUI and saves, the edited content is written to disk atomically.

## Q4: How deterministic should the session id be? What about collisions?

**Chosen answer:** the session id is the first 12 hex chars of SHA‑256 over a
canonical serialization of the diff set (sorted paths + unified diffs), as the
idea requests. On collision with different content (astronomically unlikely),
the server disambiguates by appending `-2`, `-3`, … A same-id same-content
re-open returns the existing session (idempotent re-share).

## Q5: How is the web GUI served without breaking the stdio MCP transport?

**Alternatives considered:**
- FastMCP HTTP transport plus custom routes — would force the MCP server onto
  HTTP, complicating CLI client configuration.
- A separate `aletheia serve` process the agent must start — violates the
  self-contained requirement; a CLI agent cannot be asked to manage processes.

**Chosen answer:** the MCP process lazily starts a second, loopback-only HTTP
server (Starlette + uvicorn) in a daemon thread on the first `open_review`
call. Port from `ALETHEIA_PORT` (default 8417; a later binding raises a clear
error — the user can restart with another port). The HTTP app serves a small
JSON API and the built web GUI as static files.

## Q6: Syntax highlighting: Tree-sitter/WASM or Lezer/legacy CodeMirror grammars?

**Alternatives considered:**
- `web-tree-sitter` + per-grammar `.wasm` files + `highlights.scm` queries,
  as in the Tree-sitter playground. Highest fidelity, but adds grammar
  packaging/distribution complexity (fetching wasm at runtime or bundling),
  for a read/edit diff view where fidelity of *diff* matters more than parse
  exactness.
- CodeMirror 6 with its Lezer grammars plus the legacy-mode database
  (`@codemirror/language-data`): one dependency covers most popular languages
  (Python, Java, JavaScript/TS, C/C++, Go, Rust, ...), lazy-loaded, and the
  official `@codemirror/merge` package gives an editable side-by-side diff
  editor out of the box.

**Chosen answer:** CodeMirror 6 (`@uiw/react-codemirror` + `@codemirror/merge`
+ `@codemirror/language-data`). Simplicity, robustness and packaging win;
Tree-sitter remains a documented future option (the capture-to-CM-tag mapping
is an internal detail).

## Q7: Frontend stack and build tool?

**Chosen answer:** TypeScript + React + Vite, built to a static bundle placed
inside the Python package so the wheel/uvx distribution contains the GUI
without node at install time. The built output is checked in (like Harold's
packaging of skills) so releases never depend on CI tools.

## Q8: What about state lifetime and memory growth?

**Chosen answer:** all state is in-memory and ephemeral (the process is a
per-agent-session MCP server). Baselines live until the process exits; the
session store keeps at most 100 sessions and drops the oldest
(`shortcut:` documented). Sessions with all decisions taken stay queryable so
the agent can poll a final status.

## Q9: Security posture for the web app?

**Chosen answer:** bind to `127.0.0.1` by default (`ALETHEIA_HOST` exists for
unusual local setups); no remote binding is documented or recommended. The
API acts only on paths recorded in baselines; it never writes arbitrary user
paths. Errors are returned as structured HTTP errors.

## Q10: Which files are rejected as unsupported?

**Chosen answer:** text files only. Baseline recording rejects directories
and non-UTF-8 content with a clear error naming the file; the same check
applies at `open_review` (files the agent created in the meantime must also be
UTF-8 text).

## Q11: Success criteria

- An agentic run can: record a baseline, edit files, open a review URL, and
  the user's approve/edit/reject decisions are reflected on disk correctly
  (verified by tests).
- `uvx --from aletheia aletheia` runs the MCP server on Python 3.14 and ships
  the GUI.
- Lint (ruff), type checks (mypy) and tests (pytest) pass.

*(Requirements clarification is complete; all remaining decisions are
technical design questions handled in the design phase.)*
