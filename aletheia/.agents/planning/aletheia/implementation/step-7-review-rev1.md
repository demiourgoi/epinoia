# Ponytail review — rev2 step 7 (REST + tools) — round 1

> opencode unavailable in this sandbox; ponytail checklist applied to
> commit `3ebb8b1` (step 7), including a live TestClient walk of every
> route and the fastmcp tool loop.

What this change does: the five REST routes (review payload, add, remove
(approve), rollback, save content) with 404/400/500 mapping, and the four
mirrored MCP tools with agent-manual docstrings.

Checked: error mapping per design (NotInBaseline→404, bad payloads→400,
disk failures→500 with actionable text); approve-all/reject-all compose
from the same set-of-paths operations (test); tool results carry the URL
and drift flags; no decided-status remnants.

Looks good. Ship.
