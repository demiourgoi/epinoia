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

---

# Revision 2 — baseline-only review (post-PR alignment)

After reviewing the first implementation, the model was realigned with
Zed and the author's workflow (see idea-honing Q12–Q15 and
`design/detailed-design-v2.md`, shipped on review round 2):

- **No sessions.** One baseline per MCP process (per agent conversation);
  a file is under review exactly while it has a baseline entry; approve
  (remove from baseline, adopt working dir) and reject (rollback to
  baseline, then drop the entry) are operations, not states.
- **Live diffs.** Status and GUI compare baseline vs working directory on
  demand; re-recording anchors a new change round.
- **Constant URL, free port.** `ALETHEIA_PORT` is gone; the loopback
  server binds an OS-assigned port and every URL-bearing tool result
  starts it lazily, so the URL is always live and never configured.
- **Mirrored operations:** `record_baseline`, `get_change_status`,
  `remove_from_baseline`, `rollback_to_baseline` MCP tools and the
  matching REST routes; the GUI edits write the working directory.
- **Vibe hook (v1):** `aletheia setup` installs the post_tool
  baseline-reminder hook; best-effort coaching, no enforcement.

Verification (revision 2): 64 tests green — unit (store semantics, live
kinds/changed, rollback/create/delete incl. disk-failure ordering,
save-edit guard, installer merge/idempotency, hook script subprocess
runs), web API over TestClient (404/400/500, approve/reject all
composition), fastmcp in-memory client (full agent loop), and a
real-server e2e over MCP + HTTP (live payload, save-edit + approve keeps
the tweak, reject deletes the created file, empty baseline, constant
URL). ruff + mypy clean; `uv build` wheel ships the rebuilt GUI, and
`uvx --from <wheel> aletheia --version` works on Python 3.14.

# Revision 3 — manual testing feedback from the author

Three rounds of author feedback after manual use (idea-honing Q16–Q17,
`design/detailed-design-v3.md`, design shipped on review round 2):

- **Compact diff UI.** The review page is full-width with minimal
  margins; CodeMirror is compacted by pinning its specific classes
  (`cm-gutters`, `cm-lineNumbers`, `cm-content`, `cm-scroller`). No
  global padding hacks.
- **Language highlighting out of the MVP.** In practice grammar
  loading did not kick in through the merge view, and dual highlighting
  is not simple; the diff highlighting stays. `@codemirror/language-data`
  and `@uiw/react-codemirror` were dropped entirely: the committed
  bundle went from 122 generated files to 2 (`index-*.js`/`index-*.css`),
  simplifying provenance and notices. Screenshots regenerated.
- **Baseline-aware `edit` MCP tool (opt-in).** Agents ignore the
  record_baseline request even with the hook, so Aletheia now ships
  its own edit tool with vite-`EditArgs` schema parity (file_path,
  old_string, new_string, replace_all), harness-`edit_file` semantics
  (unique match or replace_all, new != old, failure = no side effects),
  a trusted-root confinement computed once per process (git root of
  the working directory, fallback cwd, symlinks followed) matching
  the Vibe CLI filesystem-safety criteria, and automatic baseline
  registration on the file's first edit of a round. The README
  documents replacing the built-in edit tool in Vibe
  (`disabled_tools = ["edit"]` / `[tools.edit] permission = "never"`;
  MCP tools are exposed as `aletheia_edit`, so the deny-list leaves
  Aletheia's tool untouched). The hook flow remains for agents that
  keep the built-in tools.

Verification (revision 3): 94 tests green (17 new editing tests plus
two fastmcp-client edit-tool tests, including the full agent loop that
never calls record_baseline), ruff + mypy clean, `uv build` ships the
rebuilt 2-file GUI, `uvx reuse lint` fully compliant. Step 13 shipped
on review round 2 (dead directory branch removed, docstring tool-name
fix).
