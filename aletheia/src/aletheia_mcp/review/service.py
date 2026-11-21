"""ReviewService: the seam between tools/HTTP and the review core.

One process-wide instance (see `get_service`) holds the baseline and session
stores. The MCP tools and the web API both delegate here; this module never
imports transport code.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from aletheia_mcp.errors import InvalidDecisionError
from aletheia_mcp.review.baselines import BaselineStore
from aletheia_mcp.review.diffs import has_text_change
from aletheia_mcp.review.sessions import (
    FileReview,
    ReviewSession,
    SessionStore,
)
from aletheia_mcp.settings import Settings
from aletheia_mcp.web import server as web_server


class ReviewService:
    """Coordinates baselines and review sessions for one process."""

    def __init__(self, session_store: SessionStore, settings: Settings) -> None:
        self.baselines = BaselineStore()
        self.sessions = session_store
        self.settings = settings

    def record_baseline(self, paths: list[str]) -> dict[str, Any]:
        """Snapshot the pre-edit content of the given paths."""
        recorded = self.baselines.record(_resolve_all(paths))
        return {
            "recorded": sorted(str(path) for path, b in recorded.items() if b.content is not None),
            "marked_for_creation": sorted(str(path) for path, b in recorded.items() if b.content is None),
        }

    def open_review(self, paths: list[str]) -> dict[str, Any]:
        """Create (or reopen) the review session for the given paths."""
        resolved = _resolve_all(paths)
        if not resolved:
            msg = "open_review needs at least one file path."
            raise InvalidDecisionError(msg)
        files = []
        from aletheia_mcp.review.baselines import read_text_or_none

        for path in sorted(resolved):
            baseline = self.baselines.get(path)
            current = read_text_or_none(path)
            files.append(FileReview(path=path, baseline=baseline.content, current_at_open=current))
        session = self.sessions.create(files)
        web_server.ensure_running(self.settings)
        url = web_server.session_url(session.session_id, self.settings)
        changed = sum(1 for file in files if has_text_change(file.baseline, file.current_at_open))
        return {
            "session_id": session.session_id,
            "url": url,
            "status": session.status(),
            "files_changed": changed,
            "files": [_summary_file(index, file) for index, file in enumerate(session.files)],
        }

    def get_status(self, session_id: str) -> dict[str, Any]:
        return session_summary(self.sessions.get(session_id))

    def session_payload(self, session_id: str) -> dict[str, Any]:
        """Full session JSON for the web GUI (contents and diffs included)."""
        session = self.sessions.get(session_id)
        payload = session_summary(session)
        payload["files"] = [
            {
                **_summary_file(index, file),
                "baseline": file.baseline,
                "current": file.current_at_open,
                "diff": session.diff(file),
            }
            for index, file in enumerate(session.files)
        ]
        return payload

    def decide_file(self, session_id: str, file_index: int, action: str, content: str | None = None) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        file = session.decide(file_index, action, content)
        return _summary_file(file_index, file)

    def decide_all(self, session_id: str, action: str) -> dict[str, Any]:
        if action not in ("approve", "reject"):
            msg = f"Unknown bulk action {action!r}; expected approve all or reject all."
            raise InvalidDecisionError(msg)
        session = self.sessions.get(session_id)
        session.decide_all(action)  # type: ignore[arg-type]  # narrowed above
        return session_summary(session)


def _resolve_all(paths: list[str]) -> list[Path]:
    """Resolve user/agent-supplied paths (absolute or CWD-relative)."""
    return [Path(path).expanduser().resolve() for path in paths]


def _summary_file(index: int, file: FileReview) -> dict[str, Any]:
    return {
        "index": index,
        "path": str(file.path),
        "kind": file.kind,
        "status": file.status,
        "reverted": file.reverted,
    }


def session_summary(session: ReviewSession) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "status": session.status(),
        "files": [_summary_file(index, file) for index, file in enumerate(session.files)],
    }


_service_lock = threading.Lock()
_service: ReviewService | None = None


def get_service() -> ReviewService:
    """The process-wide service (lazy singleton; both tools and HTTP use it)."""
    global _service
    with _service_lock:
        if _service is None:
            from aletheia_mcp.settings import get_settings

            settings = get_settings()
            _service = ReviewService(SessionStore(settings.max_sessions), settings)
        return _service


def set_service(service: ReviewService | None) -> None:
    """Replace the process-wide service (used by tests for isolation)."""
    global _service
    with _service_lock:
        _service = service


__all__ = ["ReviewService", "get_service", "set_service"]
