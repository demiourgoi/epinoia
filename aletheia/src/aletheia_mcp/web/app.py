"""The Starlette app: review GUI static assets + JSON API (loopback only).

The API acts only on sessions created by the MCP tools; it never touches
paths outside those sessions. Errors map status codes by domain type.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from aletheia_mcp.errors import (
    AletheiaError,
    AlreadyDecidedError,
    DiskEffectError,
    InvalidDecisionError,
    UnknownSessionError,
)

DIST_DIR = Path(__file__).resolve().parent.parent / "webui" / "dist"

FALLBACK_INDEX = """<!doctype html><html><head><meta charset="utf-8">
<title>Aletheia</title></head>
<body style="font-family: sans-serif; margin: 3rem;">
<h1>Aletheia</h1>
<p>The web UI build was not found in this installation.</p>
<p>Build it with <code>make webui</code> from the repository, or reinstall
the package. The review API under <code>/api/</code> is available
regardless.</p></body></html>"""


def _error_response(error: AletheiaError, default_status: int) -> Response:
    status = {
        UnknownSessionError: 404,
        AlreadyDecidedError: 409,
        InvalidDecisionError: 400,
    }
    code = status.get(type(error), default_status)
    return JSONResponse({"error": str(error)}, status_code=code)


async def get_session(request: Request) -> Response:
    from aletheia_mcp.review.service import get_service

    session_id = request.path_params["session_id"]
    try:
        return JSONResponse(get_service().session_payload(session_id))
    except AletheiaError as error:
        return _error_response(error, 500)


async def decide_file(request: Request) -> Response:
    session_id = request.path_params["session_id"]
    index = request.path_params["index"]
    try:
        body: dict[str, Any] = json.loads(await request.body() or b"{}")
    except json.JSONDecodeError:
        return JSONResponse({"error": "Request body must be JSON."}, status_code=400)
    action = body.get("action")
    content = body.get("content")
    if not isinstance(action, str) or (content is not None and not isinstance(content, str)):
        return JSONResponse(
            {"error": "Body must contain a string 'action' and optional string 'content'."}, status_code=400
        )
    from aletheia_mcp.review.service import get_service

    try:
        summary = get_service().decide_file(session_id, int(index), action, content)
        return JSONResponse(summary)
    except ValueError:
        return JSONResponse({"error": f"Invalid file index {index!r}."}, status_code=400)
    except AletheiaError as error:
        status = 500 if isinstance(error, DiskEffectError) else None
        return _error_response(error, status or 500)


async def decide_all(request: Request) -> Response:
    session_id = request.path_params["session_id"]
    try:
        body: dict[str, Any] = json.loads(await request.body() or b"{}")
    except json.JSONDecodeError:
        return JSONResponse({"error": "Request body must be JSON."}, status_code=400)
    action = body.get("action")
    if not isinstance(action, str):
        return JSONResponse({"error": "Body must contain a string 'action'."}, status_code=400)
    from aletheia_mcp.review.service import get_service

    try:
        return JSONResponse(get_service().decide_all(session_id, action))
    except AletheiaError as error:
        status = 500 if isinstance(error, DiskEffectError) else None
        return _error_response(error, status or 500)


async def session_page(request: Request) -> Response:
    del request
    index = DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse(FALLBACK_INDEX)


async def root_page(request: Request) -> Response:
    return await session_page(request)


def create_app() -> Starlette:
    routes: list[Any] = [
        Route("/", root_page),
        Route("/s/{session_id}", session_page),
        Route("/api/sessions/{session_id}", get_session, methods=["GET"]),
        Route("/api/sessions/{session_id}/files/{index}/decision", decide_file, methods=["POST"]),
        Route("/api/sessions/{session_id}/decision", decide_all, methods=["POST"]),
    ]
    assets = DIST_DIR / "assets"
    if assets.exists():
        routes.append(Mount("/assets", app=StaticFiles(directory=assets), name="assets"))
    return Starlette(routes=routes)
