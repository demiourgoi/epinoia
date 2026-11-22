# Ponytail review — rev2 step 6 (baseline-only core) — round 1

> opencode unavailable in this sandbox; ponytail checklist applied to
> commits `1006ff8` (step 6) with the test suite traced.

What this change does: replaces sessions with a baseline-only core —
store remove/paths, live-diff ReviewService (record/remove/rollback/
save-edit/status/payload), restore-then-remove rollback under one lock,
free-port loopback server with a constant URL, settings reduced to
`ALETHEIA_HOST`.

**Must fix:**

1. **`get_change_status` before any server start returns a fake
   URL** (`review/service.py` + `web/server.py`). What this is:
   `current_url` fell back to `:0` when nothing was bound. Problem: an
   agent that polls before the first record shows the user
   `http://127.0.0.1:0`. Fix: every URL-bearing call goes through
   `ensure_running` (the URL starts the server lazily), and
   `current_url` with its `:0` fallback is deleted instead of kept as a
   predicted shape. If we skip it: dead links on a fresh conversation.

Verdict: fix 1 first.
