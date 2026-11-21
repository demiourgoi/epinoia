# Ponytail review — rev2 step 9 (hook installer + docs) — round 1

> opencode unavailable in this sandbox; ponytail checklist applied to
> commit `11ba25d`, with the hook script executed for real against
> synthetic payloads (installed copy, not the source constant).

What this change does: `aletheia setup` installs the post_tool
baseline-reminder hook (merge-safe, idempotent) and a standalone script;
server instructions and tool docstrings state the protocol; README
rewritten for revision 2; the e2e test reworked to the new flow.

Checked: merge-safety (existing hooks preserved, ours appended once,
both files re-written identically on re-install); the script is silent on
unrelated/failing payloads and never denies (strict=false default); the
installed script reads the installed file, proving self-containment;
README claims match the implemented tools and settings exactly.

Looks good. Ship.
