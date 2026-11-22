# Ponytail review — implementation step 5 — round 1

> Review subject: `code-commits`, commit `82a9fb2` (step 5 packaging,
> README, e2e). opencode unavailable in this sandbox; ponytail checklist
> applied to the diff plus the full suite and a live uvx smoke.

What this change does: it adds the real-server end-to-end test (MCP client
+ plain HTTP against a bound uvicorn on an ephemeral port), an
importlib.resources packaging test, README/CONTRIBUTING docs, and a
host:port guard in `ensure_running`.

Checked: the wheel actually ships the GUI and `uvx --from <wheel>
aletheia --version` works on Python 3.14; the e2e test asserts the
Zed-critical semantics end-to-end (saved edit stays on disk after
approve; rejected created file is deleted; mixed status reported to the
agent). `aletheia` accepts only the default command. Full suite 63
passed; ruff and mypy clean.

One consideration noted and accepted: the e2e test starts a real daemon
server thread that lives until the pytest process exits; that is the same
lifetime model as production (process-bound ephemeral state) and binding
on an OS-assigned free port avoids collisions.

Looks good. Ship.
