"""Baseline store: the recorded pre-edit snapshots of reviewed files."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from aletheia_mcp.errors import NotInBaselineError, UnsupportedFileError


@dataclass(frozen=True)
class Baseline:
    """Snapshot of one file at `record_baseline` time.

    `content is None` marks a file that did not exist yet and is planned to
    be created: rejecting it deletes it, and its diff is computed against
    the empty text.
    """

    content: str | None


def read_text_or_none(path: Path) -> str | None:
    """Read a file as UTF-8 text, or `None` when it does not exist.

    Directories and non-UTF-8 files are not reviewable: the error names the
    path so the agent can react.
    """
    if path.is_dir():
        msg = f"{str(path)!r} is a directory; only text files can be reviewed."
        raise UnsupportedFileError(msg)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        msg = f"{str(path)!r} is not valid UTF-8 text (error at byte {error.start}); binary files cannot be reviewed."
        raise UnsupportedFileError(msg) from error


class BaselineStore:
    """Thread-safe in-memory baseline map keyed by resolved path.

    An entry exists only while its file is under review: approve (remove)
    and reject (rollback) operations delete entries; re-recording a path
    overwrites its entry, which is how a new change round anchors.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._baselines: dict[Path, Baseline] = {}

    def record(self, paths: list[Path]) -> dict[Path, Baseline]:
        """Snapshot the given paths (missing ones become creation markers)."""
        recorded: dict[Path, Baseline] = {}
        for path in paths:
            recorded[path] = Baseline(read_text_or_none(path))
        resolved = dict(recorded)
        with self._lock:
            self._baselines.update(resolved)
        return recorded

    def get(self, path: Path) -> Baseline:
        with self._lock:
            try:
                return self._baselines[path]
            except KeyError:
                raise NotInBaselineError(str(path)) from None

    def remove(self, paths: list[Path]) -> None:
        """Drop entries. Every path must be in the baseline."""
        with self._lock:
            missing = [path for path in paths if path not in self._baselines]
            if missing:
                raise NotInBaselineError(str(missing[0]))
            for path in paths:
                del self._baselines[path]

    def paths(self) -> list[Path]:
        """Sorted snapshot of the paths currently under review."""
        with self._lock:
            return sorted(self._baselines)

    def __len__(self) -> int:
        with self._lock:
            return len(self._baselines)

    def clear(self) -> None:
        with self._lock:
            self._baselines.clear()
