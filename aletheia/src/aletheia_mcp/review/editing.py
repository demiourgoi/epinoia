"""Baseline-aware file changes: the trusted-root check and the operations
behind the `edit` MCP tool (exact-string edits of existing files and
whole-file creation of new ones).

The tool covers the union of the Vibe built-in `edit` and `write_file`
tools: it edits existing files with the pydantic AI harness
`FileSystem.edit_file` semantics and creates a missing file when
`old_string` is empty. It adds the automatic baseline registration that
keeps Aletheia's review honest even when the agent never calls
`record_baseline` itself.
"""

from __future__ import annotations

from pathlib import Path

from aletheia_mcp.errors import DiskEffectError, EditFailedError, OutsideTrustedRootError
from aletheia_mcp.review import disk
from aletheia_mcp.review.baselines import BaselineStore, read_text_or_none
from aletheia_mcp.setup import git_root


def trusted_root(working_dir: Path) -> Path:
    """The immutable trusted root for this process: the git repository
    root of the working directory, falling back to the working directory.

    Computed once (see ReviewService.__init__): resolving it per call
    would run a git subprocess per edit and could change the security
    answer mid-process. Paths are authorized only inside this root ---
    the same criterion the Vibe CLI applies to file tools inside its
    workspace roots.
    """
    return git_root(working_dir) or working_dir.resolve()


def contains(root: Path, path: Path) -> bool:
    """True when `path` (already resolved, symlinks followed) is inside
    or equal to `root`. `..`, absolute-outside and symlink-escape spellings
    fail alike because containment is checked after resolution."""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def apply_edit(
    *,
    root: Path,
    store: BaselineStore,
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> dict[str, object]:
    """Apply an exact-string edit or a whole-file creation, registering the
    baseline automatically.

    Evaluation order (no side effects on failure): trusted-root check →
    read and validate → baseline registration (pre-change content, only
    if absent) → atomic write. Mirrors the built-in edit/write_file tools'
    input schema and returns a result shaped like their results (plus the
    review bookkeeping).
    """
    resolved = Path(file_path).expanduser()
    resolved = (root / resolved) if not resolved.is_absolute() else resolved
    resolved = resolved.resolve()
    if not contains(root, resolved):
        msg = (
            f"Refusing to change {str(resolved)!r}: it is outside the trusted project root "
            f"{str(root)!r}. Change files inside the project."
        )
        raise OutsideTrustedRootError(msg)

    current = read_text_or_none(resolved)  # rejects directories and non-UTF-8
    if current is None:
        return _create_file(store=store, resolved=resolved, old_string=old_string, content=new_string)

    if not old_string:
        msg = (
            "old_string must not be empty when the file exists; an empty old_string would match "
            'between every character. To create a file, pass old_string="" only when it does '
            "not exist yet."
        )
        raise EditFailedError(msg)
    if old_string == new_string:
        msg = "new_string must be different from old_string."
        raise EditFailedError(msg)

    occurrences = current.count(old_string)
    if occurrences == 0:
        msg = "old_string not found in the file; no edit was applied."
        raise EditFailedError(msg)
    if occurrences > 1 and not replace_all:
        msg = (
            f"old_string occurs {occurrences} times; provide more surrounding context to make it "
            "unique, or pass replace_all=true to replace every occurrence."
        )
        raise EditFailedError(msg)

    baseline_registered = _write_with_baseline(
        store=store,
        resolved=resolved,
        content=(
            current.replace(old_string, new_string) if replace_all else current.replace(old_string, new_string, 1)
        ),
        action="edit",
    )
    message = f"Replaced {occurrences if replace_all else 1} occurrence(s) in {resolved!s}."
    return {
        "file": str(resolved),
        "message": message,
        "created": False,
        "old_string": old_string,
        "new_string": new_string,
        "baseline_registered": baseline_registered,
    }


def _create_file(*, store: BaselineStore, resolved: Path, old_string: str, content: str) -> dict[str, object]:
    """Create `resolved` with the full `content` (write_file semantics).

    The baseline entry becomes a creation marker (the file's pre-change
    state: nonexistent), so the diff shows the whole file as created and
    rejecting the change deletes it.
    """
    if old_string:
        msg = (
            f'{str(resolved)!r} does not exist. To create it, pass old_string="" and '
            "new_string with the full file content."
        )
        raise EditFailedError(msg)
    if not content:
        msg = "new_string must not be empty when creating a file."
        raise EditFailedError(msg)
    baseline_registered = _write_with_baseline(store=store, resolved=resolved, content=content, action="create")
    return {
        "file": str(resolved),
        "message": f"Created {resolved!s}.",
        "created": True,
        "baseline_registered": baseline_registered,
    }


def _write_with_baseline(*, store: BaselineStore, resolved: Path, content: str, action: str) -> bool:
    """Register the pre-change baseline when absent, then write atomically.

    Shared by the edit and create operations. On write failure the freshly
    registered entry is removed so a never-changed file never appears
    under review.
    """
    baseline_registered = resolved not in store.paths()
    if baseline_registered:
        store.record([resolved])  # pre-change state anchors the review round
    try:
        disk.write_text(resolved, content)
    except OSError as error:
        if baseline_registered:
            store.remove([resolved])  # the file was never changed: no phantom review entry
        raise DiskEffectError(str(resolved), action) from error
    return baseline_registered
