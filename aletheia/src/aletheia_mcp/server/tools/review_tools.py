"""The review tools exposed to the agent.

Tool docstrings are the agent's manual: they describe when to call the tool
during a coding task and what to do with the result. Results are compact
JSON strings (LLM-friendly and trivially parseable).
"""

from __future__ import annotations

import json

from aletheia_mcp.review.service import get_service
from aletheia_mcp.server.server import mcp


@mcp.tool
def record_baseline(paths: list[str]) -> str:
    """Record the pre-edit content of files you plan to change.

    Call this BEFORE editing each file. Snapshot the files (absolute or
    working-directory-relative paths). Files that do not exist yet are
    recorded as to-be-created, so creations are reviewable. Calling it again
    for a path overwrites the earlier baseline.

    Returns JSON {"recorded": [...], "marked_for_creation": [...]}.

    How it fits the workflow: record_baseline -> edit files (they are on
    disk, so linters/tests work) -> open_review -> share the URL with the
    user -> get_review_status to poll their decisions (rejected files are
    reverted on disk automatically).
    """
    return json.dumps(get_service().record_baseline(paths))


@mcp.tool
def open_review(paths: list[str]) -> str:
    """Open a review of your (already on-disk) edits and get a URL for the user.

    Every path must have a recorded baseline (call record_baseline first
    for any path that fails with the unknown-baseline error). Creates an
    in-memory review session comparing each file to its baseline and
    returns a URL the user opens in a browser to review a syntax-highlighted
    side-by-side diff, and to approve, edit, or reject each file or all of
    them. The call does not block: keep working, and poll with
    get_review_status.

    Returns JSON {"session_id", "url", "status", "files_changed", "files":
    [{"index", "path", "kind", "status", "reverted"}]}.
    """
    return json.dumps(get_service().open_review(paths))


@mcp.tool
def get_review_status(session_id: str) -> str:
    """Get the review decisions the user made for a session so far.

    Returns JSON {"session_id", "status", "files": [{"index", "path",
    "kind", "status", "reverted"}]}. Status is the file set's overall state:
    "pending" while any file awaits a decision, then "all_approved",
    "all_rejected", or "mixed". "reverted": true means the file was rejected
    and its pre-agent content was restored on disk. Poll this tool while you
    continue working; it never waits for the user.
    """
    return json.dumps(get_service().get_status(session_id))
