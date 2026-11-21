"""The review web server: a loopback uvicorn thread started on demand.

`ensure_running` is idempotent: the first call starts a daemon thread
serving the Starlette app and waits until the socket accepts connections,
so a session URL returned by `open_review` is always live. Bind failures
surface as ServerStartError naming ALETHEIA_PORT.
"""

from __future__ import annotations

import threading
import time

import uvicorn

from aletheia_mcp.errors import ServerStartError
from aletheia_mcp.settings import Settings
from aletheia_mcp.web.app import create_app

_START_TIMEOUT_SECS = 10.0

_lock = threading.Lock()
_server: uvicorn.Server | None = None


def base_url(settings: Settings) -> str:
    return f"http://{settings.host}:{settings.port}"


def session_url(session_id: str, settings: Settings) -> str:
    """URL of the review page for the given session id."""
    return f"{base_url(settings)}/s/{session_id}"


def ensure_running(settings: Settings) -> None:
    """Start the review server if needed; make the URL contract hold."""
    global _server
    with _lock:
        if _server is not None and _server.started:
            return
        config = uvicorn.Config(
            create_app(),
            host=settings.host,
            port=settings.port,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        threading.Thread(target=server.run, name="aletheia-review-web", daemon=True).start()
        deadline = time.monotonic() + _START_TIMEOUT_SECS
        while time.monotonic() < deadline:
            if server.started:
                _server = server
                return
            if not server.should_exit and not server.started:
                time.sleep(0.05)
        msg = (
            f"Could not start the review web server on {settings.host}:{settings.port}. "
            "If the port is already in use, set ALETHEIA_PORT to a free port and retry."
        )
        raise ServerStartError(msg)
