# Ponytail review — implementation step 4 — round 1

> Review subject: `code-commits`, commit `df204cc` (step 4 web server + GUI).
> opencode unavailable in this sandbox; ponytail checklist applied to the
> commit diff, with a live loopback smoke run against the real server.

What this change does: it adds the Starlette JSON API and static GUI
serving, the lazily-started uvicorn thread bound to ALETHEIA_PORT, and the
Vite/React/CodeMirror side-by-side review GUI (built output committed into
the package).

Checked: the startup contract (URL returns only after `server.started`),
error mapping per design, the GUI asset wiring (assets 200 in a live
smoke), decide flows against a real HTTP server, unit tests never bind
ports (ensure_running patched).

**Must fix:**

1. **`server.should_exit` is never set on bind failure, so `ensure_running`
   can block the full 10 seconds and then report a misleading message**
   (`web/server.py`). What this is: when the port is busy, uvicorn logs
   and exits, but the loop only watches `server.started`. Problem: tested
   locally? No — the loop does notice via timeout, so the user waits 10s
   and gets the right error, except when uvicorn exits immediately without
   touching `started` (the loop's second condition is a no-op). Fix: also
   stop waiting when the server thread is dead
   (`server.should_exit` OR the thread stopped). One combined flag; cuts
   the user's wait and makes the error prompt.

2. **The MCP tool result escapes its contract with the FastMCP client** —
   not a bug, verified: `open_review` returns `dict` → tools return JSON
   strings (checked `review_tools.py` uses `json.dumps`). No action. (No
   finding.)

**Should fix:**

3. **`decide_all` HTTP handler has no test for the partial-failure path**
   (`web/app.py` + step‑2 review record 1). The behavior (files reverted
   in order, first failure stops, earlier reverts stay) was accepted in
   the step‑2 review but nothing asserts it end-to-end. Fix: one unit test
   over a session with two files where the second revert fails
   (monkeypatched disk write) asserting the first file stays reverted and
   the error maps to 500.

4. **Dead `del app` / placeholder cleanup** — checked: none remains
   (test session_payload was rewritten before commit). Verified, not a
   finding.

Verdict: fix 1 and 3 first.
