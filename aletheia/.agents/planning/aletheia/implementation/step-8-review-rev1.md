# Ponytail review — rev2 step 8 (GUI) — round 1

> opencode unavailable in this sandbox; ponytail checklist applied to
> commit `8ce3d17` plus a live smoke over the real server (page + assets
> 200, save edit wrote working dir, rollback deleted the created file).

What this change does: the GUI becomes one constant-URL review page over
the new API: live list with kind/unchanged badges, per-file
approve/reject/save-edit with an unsaved-edit hint, global approve
all / reject all / refresh, empty-baseline state.

Checked: every action refetches the live payload (no stale snapshots);
buttons disable while busy; error text surfaces; the merge pane stays
editable and language-annotated as before; the build is committed.

Looks good. Ship.
