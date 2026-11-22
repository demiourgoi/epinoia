# Ponytail review — rev3 step 13 (baseline-aware `edit` tool) — round 1

> opencode unavailable in this sandbox; ponytail checklist applied to
> the working tree for step 13 (code, tests, README, REUSE entries).

What this change does: `review/editing.py` (trusted-root confinement
computed once per process, containment after symlink resolution,
`apply_edit` with trust → validate → baseline → atomic-write order),
`ReviewService.edit_file` adding the review URL, the `edit` MCP tool
with vibe-`EditArgs` schema parity, tests, and the README opt-in
section.

Checked against the v3 design delta 2: the trusted root is computed
once in `ReviewService.__init__` (no git subprocess per edit, no
mutable security answer); containment is evaluated after
`Path.resolve()` so `..`, outside-absolute and symlink-escape
spellings fail alike (test coverage confirms each); baseline
registration happens only after validation succeeds and only when the
file has no entry yet (no re-anchor within a round, new round after a
decision re-registers); the write is the existing atomic
`disk.write_text`. The evaluation order has no side effects on failure.

Two findings, both fixed in this step:

1. `apply_edit` carried a dead directory branch: `read_text_or_none`
   already raises `UnsupportedFileError` for directories before
   returning, so the `is_dir()` check after a `None` return was
   unreachable. Removed; `test_directory_rejected` still passes
   through the `read_text_or_none` path.
2. The `edit` tool docstring told agents "(register_baseline happens
   in the same call)" — the tool is `record_baseline`. Fixed the name
   so agents following the docstring call the right tool.

Also verified the README facts against the live Vibe docs (MCP tools
are exposed as `{server_name}_{tool_name}`, so ours is
`aletheia_edit`, and `disabled_tools = ["edit"]` hits only the
built-in; agent files are TOML with the same keys — an earlier draft
had a JSON agent example, corrected). `tests/conftest.py`'s `service`
fixture pins `trusted_root=tmp_path`, which is required for the
escape tests to be meaningful, and `test_review_tools.py`'s
`fresh_service` uses the default discovery.

One question weighed: should `edit_file` hold the service lock? No —
MCP stdio serves tool calls sequentially from one endpoint, the web
API does not expose edit, and `apply_edit`'s store mutations use the
store's own lock. Serializing edits behind the review lock would only
add deadlock risk against `rollback_to_baseline`.

Round 2 will re-check with the two fixes applied.
