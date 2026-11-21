"""The review web server: a loopback uvicorn thread started on demand.

The port is autodetected (uvicorn binds port 0 and the OS assigns a free
one), so no port configuration exists; the URL is returned by the MCP
tools instead. `ensure_running` is idempotent: the first call starts a
daemon thread serving the Starlette app and waits until the socket accepts
connections, so the URL a tool returns is always live. The URL is constant
for the process lifetime.
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
_url: str | None = None


def ensure_running(settings: Settings) -> str:
    """Start the review server if needed; return the constant base URL."""
    global _url
    with _lock:
        if _url is not None:
            return _url
        config = uvicorn.Config(
            create_app(),
            host=settings.host,
            port=0,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, name="aletheia-review-web", daemon=True)
        thread.start()
        deadline = time.monotonic() + _START_TIMEOUT_SECS
        while time.monotonic() < deadline:
            if server.started:
                _url = f"http://{_socket_address(server)[0]}:{_socket_address(server)[1]}"
                return _url
            if server.should_exit or not thread.is_alive():
                break
            time.sleep(0.05)
        msg = (
            f"Could not start the review web server on {settings.host} (autodetected free port). "
            "Check that the host is bindable and no firewall blocks loopback sockets."
        )
        raise ServerStartError(msg)


def _socket_address(server: uvicorn.Server) -> tuple[str, int]:
    sockets = server.servers[0].sockets if server.servers else []
    address = sockets[0].getsockname()
    return str(address[0]), int(address[1])
