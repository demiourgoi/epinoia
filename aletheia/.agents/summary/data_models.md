# Data models — aletheia

<!-- tags: data-models, state, errors -->

All review state is in-memory, keyed by resolved absolute `Path`, and lives
with the MCP process (one agent conversation).

## `Baseline` (`review/baselines.py`)

<!-- tags: baseline -->

```python
@dataclass(frozen=True)
class Baseline:
    content: str | None   # None = creation marker (file did not exist at record time)
```

- `content is None` means the file was missing when recorded (planned
  creation): its diff is computed against empty text with a `<created>`
  marker, and rejecting the change **deletes** the file.
- A `None` *current* content against a non-`None` baseline means the file was
  deleted since the baseline (`kind = "deleted"`, `<deleted>` marker).

## `BaselineStore` (`review/baselines.py`)

Thread-safe `dict[Path, Baseline]` guarded by a lock. Semantics:

- `record(paths)` — snapshot each path (`read_text_or_none`); missing files
  become creation markers; re-recording a path **overwrites** its entry (this
  is how a new change round is anchored after a decision).
- `get(path)` — raises `NotInBaselineError` when absent.
- `remove(paths)` — drops entries; **every** path must be present or the
  whole call raises `NotInBaselineError` (no partial removal).
- `paths()` — sorted snapshot; `len()`; `clear()`.

An entry exists only while its file is under review: approve
(`remove_from_baseline`) and reject (`rollback_to_baseline`) delete entries.

## Change kind and drift (`review/service.py`, `review/diffs.py`)

`_kind(baseline, current)`:

| baseline | current | kind |
| --- | --- | --- |
| `None` | anything | `"created"` |
| non-`None` | `None` | `"deleted"` |
| non-`None` | non-`None` | `"modified"` |

`has_text_change(old, new)` is `(old or "") != (new or "")`.
`unified_diff(old, new, label)` produces a `difflib` unified diff with
`{label} (before)` / `{label} (after)` headers, prefixed by the literal edge
markers `<created>` / `<deleted>` when a side is absent. Markers are part of
the canonical text hashed for session ids (`canonical_diff_text` =
`f"{path}\0{unified_diff(...)}"`).

## Payload shapes

<!-- tags: payloads -->

`get_change_status()` / `GET /api/review` file entries (status omits
contents/diff; the API includes them):

```json
{"path": "/abs/file.py", "kind": "modified", "changed": true}
{"path": "/abs/file.py", "kind": "modified", "changed": true,
 "baseline": "old text", "current": "new text", "diff": "--- ...\n+++ ..."}
```

Tool results:

```json
// record_baseline
{"url": "http://127.0.0.1:PORT/review", "recorded": ["..."], "marked_for_creation": ["..."]}
// remove_from_baseline / rollback_to_baseline
{"removed": ["..."], "files_in_baseline": 0}   // or {"rolled_back": [...], ...}
// edit (edit of an existing file)
{"file": "...", "message": "Replaced 1 occurrence(s) in ...", "created": false,
 "old_string": "...", "new_string": "...", "baseline_registered": true,
 "url": "http://127.0.0.1:PORT/review"}
// edit (creation)
{"file": "...", "message": "Created ...", "created": true,
 "baseline_registered": true, "url": "..."}
```

## Trusted root

`ReviewService.trusted_root` — a single `Path`, computed once at process start
as `git_root(Path.cwd()) or Path.cwd().resolve()`. `editing.contains(root,
path)` checks `path.relative_to(root)` after full resolution, so `..`,
absolute-outside, and symlink-escape spellings all fail.

## Error taxonomy (`errors.py`)

<!-- tags: errors -->

All extend `AletheiaError`; messages are written for an agent (name the
offending value + recovery action).

| Error | Raised when | HTTP status |
| --- | --- | --- |
| `UnsupportedFileError` | path is a directory or non-UTF-8 | 500 (tool: error text) |
| `NotInBaselineError(path)` | path not under review (never recorded, or review already ended) | 404 |
| `InvalidDecisionError` | malformed payload / empty path list | 400 |
| `DiskEffectError(path, action)` | on-disk write/delete failed (file left unchanged) | 500 |
| `OutsideTrustedRootError` | resolved `edit` path outside the trusted root | 500 (tool) |
| `EditFailedError` | agent-correctable edit input problem (no match, ambiguous, empty old_string on existing file, …) | 500 (tool) |
| `ServerStartError` | review web server could not start | — |
