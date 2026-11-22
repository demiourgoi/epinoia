"""Baseline-aware exact-string edits: the trusted-root check and the edit
operation behind the `edit` MCP tool.

The tool mirrors the Vibe built-in edit tool's input schema and the
pydantic AI harness `FileSystem.edit_file` semantics, and adds the
automatic baseline registration that keeps Aletheia's review honest even
when the agent never calls `record_baseline` itself.
"""

from __future__ import annotations

from pathlib import Path

from aletheia_mcp.errors import EditFailedError, OutsideTrustedRootError
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
    return git_root(working_dir) or working_dir


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
    """Apply an exact-string edit, registering the baseline automatically.

    Evaluation order (no side effects on failure): trusted-root check →
    read and validate → baseline registration (pre-edit content, only if
    absent) → atomic write. Mirrors the built-in edit tool's `EditArgs`
    and returns a result shaped like its `EditResult` (plus the review
    bookkeeping).
    """
    resolved = Path(file_path).expanduser()
    resolved = (root / resolved) if not resolved.is_absolute() else resolved
    resolved = resolved.resolve()
    if not contains(root, resolved):
        msg = (
            f"Refusing to edit {str(resolved)!r}: it is outside the trusted project root "
            f"{str(root)!r}. Edit files inside the project."
        )
        raise OutsideTrustedRootError(msg)

    if old_string == new_string:
        msg = "new_string must be different from old_string."
        raise EditFailedError(msg)

    current = read_text_or_none(resolved)  # rejects directories and non-UTF-8
    if current is None:
        msg = (
            f"{str(resolved)!r} does not exist. This tool edits existing files; create the file "
            "first (and start its review with record_baseline when you plan to review it)."
        )
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

    baseline_registered = resolved not in store.paths()
    if baseline_registered:
        store.record([resolved])  # pre-edit content anchors the review round

    updated = current.replace(old_string, new_string) if replace_all else current.replace(old_string, new_string, 1)
    disk.write_text(resolved, updated)
    message = f"Replaced {occurrences if replace_all else 1} occurrence(s) in {resolved!s}."
    return {
        "file": str(resolved),
        "message": message,
        "old_string": old_string,
        "new_string": new_string,
        "baseline_registered": baseline_registered,
    }
