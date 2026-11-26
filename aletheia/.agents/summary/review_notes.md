# Review notes — aletheia knowledge base

<!-- tags: review, gaps, consistency -->

Consistency and completeness review of the docs in
`aletheia/.agents/summary/`, produced alongside their generation.

## Consistency check

- Tool names, signatures, and JSON result shapes in `interfaces.md` match
  `server/tools/review_tools.py` and the payload builders in
  `review/service.py` (`record_baseline`, `get_change_status`,
  `remove_from_baseline`, `rollback_to_baseline`, `edit_file`,
  `review_payload`).
- HTTP routes and status codes in `interfaces.md` match `web/app.py`
  (`_error_response` mapping: `NotInBaselineError`→404,
  `InvalidDecisionError`→400, disk→500) and the `LoopbackGuard` rules.
- Invariants in `architecture.md` (lazy server, constant URL, in-memory
  baseline, trusted root, atomic writes, UTF-8 only, no parent-dir creation)
  are all implemented in `web/server.py`, `review/service.py`,
  `review/editing.py`, `review/disk.py`, and `review/baselines.py`
  respectively, and cross-checked against `DEVELOPER_GUIDE.md`.
- `workflows.md` flow diagrams follow the code paths in `review/service.py`
  (including the rollback precheck-before-disk ordering) and
  `tests/integration/test_e2e.py`.
- No inconsistencies found between these docs and the source. The
  human-written `README.md` / `DEVELOPER_GUIDE.md` agree with the code and are
  used as corroboration, not copied verbatim.

## Completeness check / known gaps

- **GUI internals are documented at the component level only.**
  `webui/src/DiffPane.tsx`, `styles.css`, and `main.tsx` are not described
  line-by-line; the docs cover the API client (`api.ts`) and the page
  behavior (`App.tsx`). Sufficient for navigation; open the sources for
  styling or merge-view specifics.
- **`review/diffs.py::canonical_diff_text`** (session-id hashing) is
  documented in `data_models.md` but no current caller besides tests was
  identified during analysis; it may be forward-looking API. Flagged as an
  observation, not an error.
- **Unit test internals** are listed per module in `components.md` but not
  summarized case-by-case; consult `tests/unit/` directly.
- **PDD planning artifacts** in `.agents/planning/aletheia/` are inventoried
  but not summarized; they are historical design material governed by the
  PDD skill, not day-to-day reference.
- **`.local/`, `.venv/`, caches** are gitignored environment directories and
  intentionally undocumented.

## Recommendations

- When adding an MCP tool or HTTP route, update `interfaces.md` (protocol
  tables), `components.md` (module responsibilities), and `workflows.md`
  (affected flow) in the same change.
- When changing the GUI, rebuild with `make webui` and commit the dist; do
  not hand-edit `src/aletheia_mcp/webui/dist`.
- Keep `aletheia/AGENTS.md` (the consolidated entry point) in sync by
  re-running codebase-summary after structural changes; its Custom
  Instructions section is human-maintained and must be preserved.
