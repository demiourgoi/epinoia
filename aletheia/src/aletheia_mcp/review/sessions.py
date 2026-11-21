"""Review sessions: per-file statuses, decisions, and the session store."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal

from aletheia_mcp.errors import AlreadyDecidedError, InvalidDecisionError
from aletheia_mcp.review import disk
from aletheia_mcp.review.diffs import canonical_diff_text, unified_diff

FileStatus = Literal["pending", "edited", "approved", "rejected"]
Action = Literal["approve", "reject", "save_edit"]

ID_DIGEST_CHARS = 12


def file_change_kind(baseline: str | None, current: str | None) -> Literal["created", "deleted", "modified"]:
    """How the file changed between baseline and review time."""
    if baseline is None:
        return "created"
    if current is None:
        return "deleted"
    return "modified"


@dataclass
class FileReview:
    """One file of a review session.

    `baseline` is `None` for a planned creation; `current_at_open` is `None`
    when the file was absent when the review was opened. Only `approved` and
    `rejected` are decided statuses; `edited` (saved user edits) is pending.
    """

    path: Path
    baseline: str | None
    current_at_open: str | None
    status: FileStatus = "pending"

    @property
    def kind(self) -> str:
        return file_change_kind(self.baseline, self.current_at_open)

    @property
    def decided(self) -> bool:
        return self.status in ("approved", "rejected")

    @property
    def reverted(self) -> bool:
        return self.status == "rejected"


@dataclass
class ReviewSession:
    """A set of files reviewed against their baselines."""

    session_id: str
    files: list[FileReview]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    canonical_diff: str = ""
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def decide(self, index: int, action: str, content: str | None = None) -> FileReview:
        """Apply a decision to the file at `index`, effecting the disk first.

        State follows disk: the status only changes after the disk effect
        succeeded. Decided files raise AlreadyDecidedError. `save_edit`
        requires `content`.
        """
        if not 0 <= index < len(self.files):
            msg = f"File index {index} is out of range (session has {len(self.files)} files)."
            raise InvalidDecisionError(msg)
        file = self.files[index]
        with self._lock:
            if file.decided:
                raise AlreadyDecidedError(str(file.path), file.status)
            if action == "approve":
                file.status = "approved"
            elif action == "reject":
                if file.baseline is None:
                    disk.delete(file.path)
                else:
                    disk.write_text(file.path, file.baseline)
                file.status = "rejected"
            elif action == "save_edit":
                if content is None:
                    msg = "save_edit requires the edited file content."
                    raise InvalidDecisionError(msg)
                disk.write_text(file.path, content)
                file.status = "edited"
            else:
                msg = f"Unknown decision action {action!r}; expected approve, reject or save_edit."
                raise InvalidDecisionError(msg)
        return file

    def decide_all(self, action: Action) -> list[FileReview]:
        """Apply approve (or reject) to every undecided file, in order."""
        decided: list[FileReview] = []
        for index, file in enumerate(self.files):
            if file.decided:
                continue
            decided.append(self.decide(index, action))
        return decided

    def status(self) -> Literal["pending", "all_approved", "all_rejected", "mixed"]:
        if any(not file.decided for file in self.files):
            return "pending"
        statuses = {file.status for file in self.files}
        if statuses == {"approved"}:
            return "all_approved"
        if statuses == {"rejected"}:
            return "all_rejected"
        return "mixed"

    def diff(self, file: FileReview) -> str:
        return unified_diff(file.baseline, file.current_at_open, str(file.path))


def compute_session_id(files: list[FileReview]) -> tuple[str, str]:
    """Deterministic id (hash of the canonical diff set) plus that text.

    Identical changes always map to the same id (project requirement).
    """
    canonical = "\n".join(
        canonical_diff_text(file.baseline, file.current_at_open, str(file.path))
        for file in sorted(files, key=lambda file: str(file.path))
    )
    return sha256(canonical.encode("utf-8")).hexdigest()[:ID_DIGEST_CHARS], canonical


class SessionStore:
    """Thread-safe in-memory session map; bounded, oldest dropped.

    shortcut: sessions are capped at `max_sessions` (default 100, env
    ALETHEIA_MAX_SESSIONS). A cap large for a single agent run; dropping the
    oldest evicts baselines the user may still have open in a browser tab.
    Capped, documented, fine at the expected load.
    """

    def __init__(self, max_sessions: int) -> None:
        self.max_sessions = max_sessions
        self._lock = threading.Lock()
        self._sessions: dict[str, ReviewSession] = {}

    def create(self, files: list[FileReview]) -> ReviewSession:
        """Create a session; reopening the identical diff returns it."""
        digest, canonical = compute_session_id(files)
        with self._lock:
            existing = self._sessions.get(digest)
            if existing is not None and existing.canonical_diff == canonical:
                return existing
            session_id = digest
            suffix = 1
            while session_id in self._sessions:
                suffix += 1
                session_id = f"{digest}-{suffix}"
            session = ReviewSession(session_id=session_id, files=files, canonical_diff=canonical)
            self._sessions[session_id] = session
            while len(self._sessions) > self.max_sessions:
                oldest = next(iter(self._sessions))
                del self._sessions[oldest]
            return session

    def get(self, session_id: str) -> ReviewSession:
        from aletheia_mcp.errors import UnknownSessionError

        with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError:
                raise UnknownSessionError(session_id) from None

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)
