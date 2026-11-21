"""Diff computation and the canonical text that session ids hash."""

from __future__ import annotations

import difflib

CREATED_MARKER = "<created>"
DELETED_MARKER = "<deleted>"


def unified_diff(old: str | None, new: str | None, label: str) -> str:
    """Unified diff between the two texts, with stable edge markers.

    `None` means the file is absent on that side: a `None` baseline is a
    file planned for creation (`<created>`), a `None` current content a
    file deleted since the baseline (`<deleted>`). Markers are part of both
    the displayed header and the id hash input, so they must be literal and
    stable.
    """
    markers = ""
    if old is None:
        markers = CREATED_MARKER
        old = ""
    if new is None:
        markers = f"{markers} {DELETED_MARKER}".strip()
        new = ""
    body = "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{label} (before)",
            tofile=f"{label} (after)",
        )
    )
    return f"{markers}\n{body}" if markers else body


def canonical_diff_text(old: str | None, new: str | None, path: str) -> str:
    """The per-file line of the canonical text that session ids hash."""
    return f"{path}\0{unified_diff(old, new, path)}"


def has_text_change(old: str | None, new: str | None) -> bool:
    """True when the content differs (for summary counts)."""
    return (old or "") != (new or "")
