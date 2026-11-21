"""Domain errors surfaced to MCP tool callers and HTTP clients.

Every error message is written for an agent: it names the offending value
and the action needed to recover.
"""


class AletheiaError(Exception):
    """Base class for all Aletheia domain errors."""


class UnsupportedFileError(AletheiaError):
    """A path is not a reviewable UTF-8 text file (directory or non-UTF-8)."""


class UnknownBaselineError(AletheiaError):
    """A path has no recorded baseline: `record_baseline` must be called."""

    def __init__(self, path: str) -> None:
        super().__init__(
            f"No baseline recorded for {path!r}. Call record_baseline with this path "
            "before editing it, then call open_review again."
        )


class UnknownSessionError(AletheiaError):
    """No review session exists with the given id."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Unknown review session {session_id!r}. Use the session_id returned by open_review.")


class AlreadyDecidedError(AletheiaError):
    """The file already got a final approve/reject decision."""

    def __init__(self, path: str, status: str) -> None:
        super().__init__(
            f"{path!r} was already {status}. Rejected files were reverted on disk; "
            "open a new review for further changes."
        )


class InvalidDecisionError(AletheiaError):
    """A decision payload is malformed or unknown."""


class ServerStartError(AletheiaError):
    """The review web server could not be started (for example a busy port)."""
