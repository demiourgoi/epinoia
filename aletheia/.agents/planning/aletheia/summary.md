# Aletheia — PDD project summary

**What shipped:** an MCP server (command `aletheia`, Python 3.14, FastMCP)
that gives terminal coding agents Zed-style asynchronous change review:

- `record_baseline(paths)`: pre-edit snapshots (with creation markers).
- `open_review(paths)`: deterministic hashed session id (hash of the diff
  set), a non-blocking review URL on a lazily started loopback web server
  (port from `ALETHEIA_PORT`, default 8417).
- `get_review_status(session_id)`: non-blocking poll of the user's
  decisions.

The review GUI (Vite + React + TypeScript, CodeMirror 6 merge view +
language data) shows a side-by-side, syntax-highlighted, editable diff per
file; the user can approve, edit-then-approve, or reject each file, or act
on all files at once. Approvals keep the disk state, edits are written
atomically, rejections roll files back to their baseline on disk
immediately (created files are deleted). The built GUI is committed inside
the package, so `uvx` ships it; `uvx --from <wheel> aletheia` was verified.

**Verification:** 63 tests (unit + real-server e2e) plus ruff/mypy/uv
lock, and live smokes (bus error message, asset serving, revert-on-disk).
The e2e test exercises the entire product loop through MCP tools and HTTP.

**PDD record:** rough idea → idea honing (agent-answered per the
unattended mandate) → research (Zed review model, FastMCP/packaging, diff
editor options) → detailed design (2 ponytail rounds, ship on round 2) →
implementation plan (5 steps, each committed and reviewed; step reviews
shipped on round 1 except step 1 (round 2) and step 4 (round 2); all
within the 3-round cap) → final review below.

**Deliberate limits (documented in the design):** file-level review (no
hunks), snapshot-at-open (no live re-diff while the user reviews),
in-memory state (nothing survives restart), text-only files, one
host:port per process.
