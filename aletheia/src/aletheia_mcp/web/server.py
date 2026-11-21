"""Session URLs for the review web server.

Step 3 states the URL contract; step 4 makes the URL actually serve the
review GUI by starting a loopback uvicorn thread in `ensure_running`.
"""

from aletheia_mcp.settings import Settings


def base_url(settings: Settings) -> str:
    return f"http://{settings.host}:{settings.port}"


def session_url(session_id: str, settings: Settings) -> str:
    """URL of the review page for the given session id."""
    return f"{base_url(settings)}/s/{session_id}"


def ensure_running(settings: Settings) -> None:
    """No-op until step 4 replaces it with the real server start."""
