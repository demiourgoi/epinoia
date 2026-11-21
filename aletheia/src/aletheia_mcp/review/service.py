"""ReviewService: the seam between tools/HTTP and the review core.

One process-wide instance (see `get_service`) holds the baseline store.
The MCP tools and the web API both delegate here; this module never
imports transport code. There is a single baseline per process (one
agent conversation): an entry exists only while its file is under review.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from aletheia_mcp.errors import DiskEffectError, InvalidDecisionError
from aletheia_mcp.review import disk
from aletheia_mcp.review.baselines import BaselineStore, read_text_or_none
from aletheia_mcp.review.diffs import has_text_change, unified_diff
from aletheia_mcp.settings import Settings
from aletheia_mcp.web import server as web_server


class ReviewService:
    """Coordinates the baseline and live diffs for one process."""

    def _url(self) -> str:
        """The review URL; starts the loopback server on first use."""
        return web_server.ensure_running(self.settings)

    def __init__(self, settings: Settings, store: BaselineStore | None = None) -> None:
        self.settings = settings
        self.baselines = store or BaselineStore()
        self._lock = threading.Lock()

    def record_baseline(self, paths: list[str]) -> dict[str, Any]:
        """Snapshot the pre-edit content of the given paths (add to the baseline)."""
        resolved = _resolve_all(paths)
        if not resolved:
            msg = "record_baseline needs at least one file path."
            raise InvalidDecisionError(msg)
        recorded = self.baselines.record(resolved)
        url = self._url()
        return {
            "url": url,
            "recorded": sorted(str(path) for path, b in recorded.items() if b.content is not None),
            "marked_for_creation": sorted(str(path) for path, b in recorded.items() if b.content is None),
        }

    def get_change_status(self) -> dict[str, Any]:
        """Live drift of every baseline file against the working directory.

        Cheap by construction: one file read per baseline path, no unified
        diff and no contents in the payload.
        """
        files = []
        for path in self.baselines.paths():
            baseline = self.baselines.get(path).content
            current = read_text_or_none(path)
            files.append({
                "path": str(path),
                "kind": _kind(baseline, current),
                "changed": has_text_change(baseline, current),
            })
        return {"url": self._url(), "files_in_baseline": len(files), "files": files}

    def remove_from_baseline(self, paths: list[str]) -> dict[str, Any]:
        """Adopt the working directory for the given paths (approve-file)."""
        resolved = _resolve_all(paths)
        if not resolved:
            msg = "remove_from_baseline needs at least one file path."
            raise InvalidDecisionError(msg)
        self.baselines.remove(resolved)
        return {
            "removed": sorted(str(path) for path in resolved),
            "files_in_baseline": len(self.baselines),
        }

    def rollback_to_baseline(self, paths: list[str]) -> dict[str, Any]:
        """Restore pre-change content on disk, then end review of the paths."""
        resolved = _resolve_all(paths)
        if not resolved:
            msg = "rollback_to_baseline needs at least one file path."
            raise InvalidDecisionError(msg)
        with self._lock:
            for path in resolved:
                baseline = self.baselines.get(path).content
                try:
                    if baseline is None:
                        disk.delete(path)
                    else:
                        disk.write_text(path, baseline)
                except OSError as error:
                    raise DiskEffectError(str(path), "rollback") from error
                self.baselines.remove([path])
        return {
            "rolled_back": sorted(str(path) for path in resolved),
            "files_in_baseline": len(self.baselines),
        }

    def write_file_content(self, path: str, content: str) -> None:
        """Write user-edited content to the working directory (GUI save-edit)."""
        resolved = _resolve_all([path])
        self.baselines.get(resolved[0])  # only files under review are editable here
        try:
            disk.write_text(resolved[0], content)
        except OSError as error:
            raise DiskEffectError(str(resolved[0]), "save_edit") from error

    def review_payload(self) -> dict[str, Any]:
        """Full live review payload for the web GUI (contents and diffs)."""
        files = []
        for path in self.baselines.paths():
            baseline = self.baselines.get(path).content
            current = read_text_or_none(path)
            files.append({
                "path": str(path),
                "kind": _kind(baseline, current),
                "changed": has_text_change(baseline, current),
                "baseline": baseline,
                "current": current,
                "diff": unified_diff(baseline, current, str(path)),
            })
        return {"url": self._url(), "files": files}


def _kind(baseline: str | None, current: str | None) -> str:
    if baseline is None:
        return "created"
    if current is None:
        return "deleted"
    return "modified"


def _resolve_all(paths: list[str]) -> list[Path]:
    """Resolve user/agent-supplied paths (absolute or CWD-relative)."""
    return [Path(path).expanduser().resolve() for path in paths]


_service_lock = threading.Lock()
_service: ReviewService | None = None


def get_service() -> ReviewService:
    """The process-wide service (lazy singleton; both tools and HTTP use it)."""
    global _service
    with _service_lock:
        if _service is None:
            from aletheia_mcp.settings import get_settings

            _service = ReviewService(get_settings())
        return _service


def set_service(service: ReviewService | None) -> None:
    """Replace the process-wide service (used by tests for isolation)."""
    global _service
    with _service_lock:
        _service = service


__all__ = ["ReviewService", "get_service", "set_service"]
