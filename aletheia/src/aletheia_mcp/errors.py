"""Domain errors surfaced to MCP tool callers and HTTP clients.

Every error message is written for an agent: it names the offending value
and the action needed to recover.
"""


class AletheiaError(Exception):
    """Base class for all Aletheia domain errors."""


class UnsupportedFileError(AletheiaError):
    """A path is not a reviewable UTF-8 text file (directory or non-UTF-8)."""


class NotInBaselineError(AletheiaError):
    """A path has no baseline entry: it is not under review."""

    def __init__(self, path: str) -> None:
        super().__init__(
            f"{path!r} is not in the baseline, so it is not under review. Either it "
            "was never recorded (call record_baseline before editing it) or its "
            "review already ended (approve/remove or reject/rollback drops the "
            "entry; record_baseline starts a new round)."
        )


class InvalidDecisionError(AletheiaError):
    """A request payload is malformed or an operation got no paths."""


class DiskEffectError(AletheiaError):
    """An on-disk effect could not be applied (file, action, cause)."""

    def __init__(self, path: str, action: str) -> None:
        super().__init__(
            f"Could not apply {action!r} to {path!r}: the file was left unchanged. "
            "Check permissions and that no parent directory is missing."
        )


class OutsideTrustedRootError(AletheiaError):
    """A resolved path lies outside the trusted project root."""


class EditFailedError(AletheiaError):
    """An edit could not be applied (agent-correctable: bad input)."""


class ServerStartError(AletheiaError):
    """The review web server could not be started."""
