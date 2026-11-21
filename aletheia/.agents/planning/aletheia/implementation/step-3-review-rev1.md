# Ponytail review — implementation step 3 — round 1

> Review subject: `code-commits`, commit `cc539e5` (step 3 tools).
> opencode unavailable in this sandbox; ponytail checklist applied to the
> commit diff plus callers in `tests/unit/test_review_tools.py`.

What this change does: it adds a ReviewService seam over the step-2 core
and the three MCP tools (record_baseline, open_review, get_review_status)
returning JSON strings, plus the URL contract stub in `web/server.py`.

Checked: tool error paths surface as ToolError with the actionable messages
(tested); the in-memory MCP client drives the real decorated functions; the
service singleton is used by nothing before step 4 exists (grep: only
tools import `get_service`).

**Must fix:**

1. **`open_review` resolves paths against the MCP server's CWD, but the GUI
   contract later shows absolute paths — mixed story is fine, yet the
   *missing-file validation differs between record and open*.**
   (`review/service.py`, `open_review`). What this is: open_review reads the
   current content with `read_text_or_none` *after* `baselines.get`.
   Problem: none for correctness — baseline lookup raising first is the
   better error. Checked: covered. Recording this as verified, not a
   finding.

No must-fix or should-fix findings: the seam is thin, tested, and every
result shape is asserted. One lean note: `decide_all`'s action validation
duplicates the session-level check — harmless duplication that guards the
HTTP layer with a better message; keep.

Looks good. Ship.
