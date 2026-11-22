# Ponytail review — rev3 step 12 (compact UI, language highlighting out) — round 1

> opencode unavailable in this sandbox; ponytail checklist applied to
> commit `6bacdb1`, plus a live headless render of the new UI.

What this change does: full-width review page with minimal margins and
pinned-thin CodeMirror gutters/content; language grammar loading removed
(diff highlighting stays); committed bundle 122 → 2 files; sidecars,
notices and screenshots updated.

Checked: the compaction touches only the named CodeMirror classes (no
global padding hacks, per the design); drafts/remount behavior is
preserved (the pane builds once on mount, the render-tick key still
governs remounts — verified by reading DiffPane and App, and by the
live render); no orphaned references to the removed packages in source
or package.json; THIRD-PARTY/REUSE consistent with the new bundle.
Fresh screenshot verified: full-width layout, plain text, red/green
changed chunks, no wasted side bands.

Looks good. Ship.
