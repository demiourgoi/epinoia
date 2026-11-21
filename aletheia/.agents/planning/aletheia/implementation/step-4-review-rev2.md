# Ponytail review — implementation step 4 — round 2

> Round-1 fixes verified first: `ensure_running` now stops waiting when the
> server thread dies (verified live: a busy port fails in 0.05s with the
> intended ServerStartError naming ALETHEIA_PORT), and the decide-all
> partial-failure path has an end-to-end test (first file stays reverted on
> disk, failed file stays pending, HTTP 500).

Checked: startup, error mapping, asset serving, and all decision flows
hold at the expected load (one agent, one browser tab). 61 tests, ruff,
mypy green.

Looks good. Ship.
