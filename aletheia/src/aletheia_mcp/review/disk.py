"""Atomic on-disk effects: the only module that writes or deletes files.

Writes are atomic for the reader (linter, agent): the file is replaced by
`os.replace` on the same filesystem, so a file is either fully the old or
fully the new content. The server never creates parent directories.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

TEMP_PREFIX = ".aletheia-"


def write_text(path: Path, content: str) -> None:
    """Atomically replace `path` with `content` (UTF-8).

    Raises OSError when the parent directory does not exist: the server must
    never create directories.
    """
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=TEMP_PREFIX)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        _remove(Path(tmp_name))
        raise


def delete(path: Path) -> None:
    """Delete `path` if it exists (used to roll back creation)."""
    _remove(path)


def _remove(path: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        path.unlink()
