# Detailed design: Aletheia — revision 3 (delta on v2)

Revision 3 records two changes decided from the author's manual testing of
the second prototype, answering idea-honing Q16–Q17. It is a delta on
`detailed-design-v2.md` (baseline-only review, constant `/review` URL,
free port): everything not restated here is unchanged.

## Delta 1 — Diff UI uses the width; language highlighting is out of the MVP

- **Full-width review page.** The page drops its 1100 px `max-width` and
  the generous paddings; the file list narrows and the diff panes get
  the reclaimed space. The compaction pins the specific CodeMirror
  classes (`cm-gutters`, `cm-content`, and the merge view's pane gap)
  rather than global padding, so a CodeMirror update cannot silently
  widen the UI again. Diff view is the product — margins are
  overhead.
- **Language grammars removed.** The GUI no longer loads
  `@codemirror/language-data`; the diff highlighting of
  `@codemirror/merge` (red/green changed chunks, chunk revert controls)
  is kept and is the MVP's highlighting. The committed `webui/dist`
  shrinks accordingly (no per-language chunks; the only bundled libs
  are CodeMirror core+merge and React). Language-annotated merging
  remains a documented future option (attach a grammar extension to the
  merge panes).

## Delta 2 — A baseline-aware `edit` tool (opt-in replacement for the built-in edit tool)

Manual testing shows agents skip `record_baseline` even with the
reminder hook. The reliable fix is to make the edit itself register the
baseline.

### Tool contract

```
edit(file_path: str, old_string: str, new_string: str, replace_all: bool = False)
```

- **Schema parity** with the Vibe built-in edit tool
  (`vibe/core/tools/builtins/edit.py`: `EditArgs`) — same argument names,
  types, defaults and meanings, so agents and prompts transfer directly.
- **Semantics** follow the pydantic AI harness `FileSystem.edit_file` /
  the Vibe tool: exact-string replacement against the on-disk UTF-8 text;
  `old_string` must occur exactly once unless `replace_all` (0 matches
  and >1 matches are agent-correctable errors naming the count);
  `new_string == old_string` is rejected; the write is atomic (temp file
  + `os.replace`, dir-local). A missing file, a directory, and non-UTF-8
  content are clear errors (creations are out of scope: the tool mirrors
  `edit`, not `write_file`).
- **Trusted root check, vibe's criteria** (`vibe/core/tools/utils.py`:
  `is_path_within_workdir` / `resolve_file_tool_permission`): the
  supplied path — absolute or CWD-relative, `~` expanded — is resolved
  with symlinks and `..` followed, and must stay inside the trusted
  root; otherwise the call fails with an error naming both the path and
  the root. The **trusted root** is the git repository root of the
  working directory (falling back to the working directory when no
  repository is found) — the same root Vibe authors file-tool calls
  against inside its workspace roots, and the same placement rule this
  project already uses for the hook install. It is computed **once**, at
  service construction (the MCP process starts in the project directory,
  the same assumption relative-path resolution already makes), and held
  immutable for the process; no `git` subprocess runs per tool call.
- **Evaluation order (no side effects on failure):** trusted-root check
  → read and validate (existence, UTF-8, unique match unless
  `replace_all`, `new != old`) → baseline registration (pre-edit
  content, only if absent) → atomic write. A failing edit never
  registers or overwrites a baseline entry.
- **Automatic baseline:** before applying the edit, if the path is not
  in the baseline, its pre-edit content is recorded first (the same call
  returns `baseline_registered: true`). A file whose review already
  ended and is edited again re-enters review from the new content —
  `record_baseline` semantics per path, unchanged elsewhere.
- **Result** mirrors the built-in tool's `EditResult` fields the agent
  cares about (`file`, `message`, `old_string`, `new_string`) plus
  `baseline_registered` and the review `url`.

### Relationship to the existing flows

- Purely **additive**: `record_baseline`, `get_change_status`,
  `remove_from_baseline`, `rollback_to_baseline`, the REST/GUI surface,
  and the `aletheia setup` hook are unchanged. A user who prefers the
  built-in edit tool keeps the hook-based flow; a user who wants a
  guaranteed baseline switches the agent's editing to this tool.
- **Vibe opt-in configuration** (documented in the README): forbid the
  built-in edit tool and route editing through this server, e.g. with
  `.vibe/config.toml` / agent-file entries (`[tools.edit] permission =
  "never"` or `disabled_tools = ["edit"]`) alongside the existing
  `mcpServers` entry for aletheia; the MCP tool then appears as
  `aletheia`'s edit tool. (Exact key names per the Vibe configuration
  reference; the REM documents where to verify them.)

### Components and testing

- `review/editing.py`: `trusted_root() -> Path` (git root of the
  service's working directory, fallback to it), `contains(root, path)`
  (resolution with symlinks followed, containment check),
  `apply_edit(...)` implementing the contract above over the existing
  baseline store and atomic disk writer, all under the store/operation
  locks.
- `server/tools/review_tools.py`: the `edit` MCP tool with an
  agent-manual docstring (parity, trusted root, auto-baseline).
- Tests: schema parity (arguments), unique-match and replace_all
  semantics, error cases (0 matches, N matches, same strings, missing
  file, binary, directory), trusted-root acceptance from a subdirectory
  and rejection of `..`, absolute-outside and symlink-escape paths,
  auto-baseline registration (first edit records, subsequent edits don't
  overwrite the round anchor, decided files start a new round), the
  full agent loop over the fastmcp client, and REST/GUI regression.
- GUI: margin compaction verified by a fresh headless screenshot; no
  functional GUI change.
