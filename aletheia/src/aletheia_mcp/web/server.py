"""The review web server: a loopback uvicorn thread started on demand.

The port is autodetected (uvicorn binds port 0 and the OS assigns a free
one), so no port configuration exists; the URL is returned by the MCP
tools instead. `ensure_running` is idempotent: the first call starts a
daemon thread serving the Starlette app and waits until the socket
accepts connections, so the URL a tool returns is always live. The URL is
constant for the process lifetime.
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
_serving_host: str | None = None
_serving_port: int | None = None


def ensure_running(settings: Settings) -> str:
    """Start the review server if needed; return the constant base URL."""
    global _server, _serving_host, _serving_port
    with _lock:
        if _server is not None and _server.started:
            return current_url(settings)
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
                _server = server
                _serving_host, _serving_port = _socket_address(server)
                return current_url(settings)
            if server.should_exit or not thread.is_alive():
                break
            time.sleep(0.05)
        msg = (
            f"Could not start the review web server on {settings.host} (autodetected free port). "
            "Check that the host is bindable and no firewall blocks loopback sockets."
        )
        raise ServerStartError(msg)


def current_url(settings: Settings) -> str:
    """The review URL; before the server starts it is the predicted shape."""
    host = _serving_host or settings.host
    port = _serving_port or 0
    return f"http://{host}:{port}"


def _socket_address(server: uvicorn.Server) -> tuple[str, int]:
    sockets = server.servers[0].sockets if server.servers else []
    address = sockets[0].getsockname()
    return str(address[0]), int(address[1])
