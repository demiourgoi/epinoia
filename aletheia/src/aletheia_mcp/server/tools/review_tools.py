"""The review tools exposed to the agent.

Tool docstrings are the agent's manual: they describe when to call the
tool during a coding task and what to do with the result. Results are
compact JSON strings (LLM-friendly and trivially parseable).
"""

from __future__ import annotations

import json

from aletheia_mcp.review.service import get_service
from aletheia_mcp.server.server import mcp


@mcp.tool
def record_baseline(paths: list[str]) -> str:
    """Record the pre-edit content of files you plan to change (baseline).

    Call this BEFORE editing each file (paths: absolute or working-directory
    relative). Files that do not exist yet are recorded as to-be-created.
    Calling it again for a path overwrites the earlier baseline, which is
    how a new change round is anchored after a previous one was decided.

    Starts the review web server on first use and returns JSON
    {"url", "recorded": [...], "marked_for_creation": [...]}: show "url" to
    the user so they can review your changes in a browser while you work.
    """
    return json.dumps(get_service().record_baseline(paths))


@mcp.tool
def get_change_status() -> str:
    """Get the live status of the change under review (never blocks).

    Returns JSON {"url", "files_in_baseline", "files": [{"path", "kind"
    ("created"|"deleted"|"modified"), "changed"}]}. "changed": false means
    the working directory currently matches the baseline for that file.
    The review is asynchronous: keep working and poll this tool.
    """
    return json.dumps(get_service().get_change_status())


@mcp.tool
def remove_from_baseline(paths: list[str]) -> str:
    """Approve files: adopt the working directory and end their review.

    This keeps the current on-disk content and removes the paths from the
    baseline (they are no longer under review). Use it when the user
    approves changes, for a subset of files ("approve all" passes every
    path from get_change_status).
    """
    return json.dumps(get_service().remove_from_baseline(paths))


@mcp.tool
def rollback_to_baseline(paths: list[str]) -> str:
    """Reject files: restore their pre-change content on disk, ending review.

    Writes the recorded baseline content back to disk atomically (deleting
    a to-be-created file) and removes the paths from the baseline. Use it
    when the user rejects changes, for a subset of files ("reject all"
    passes every path from get_change_status). Files you edit again
    afterwards must be re-registered with record_baseline.
    """
    return json.dumps(get_service().rollback_to_baseline(paths))
