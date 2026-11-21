"""The Starlette app: review GUI static assets + JSON API (loopback only).

The API acts only on paths recorded in the baseline; it never touches
paths outside it. Errors map status codes by domain type.
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
    DiskEffectError,
    InvalidDecisionError,
    NotInBaselineError,
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
        NotInBaselineError: 404,
        InvalidDecisionError: 400,
    }
    code = status.get(type(error), default_status)
    return JSONResponse({"error": str(error)}, status_code=code)


async def _body(request: Request) -> dict[str, Any]:
    raw = await request.body()
    parsed = _json_or_none(raw) or {}
    if not isinstance(parsed, dict):
        msg = "Request body must be a JSON object."
        raise InvalidDecisionError(msg)
    return parsed


def _json_or_none(raw: bytes) -> object | None:
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError as error:
        msg = "Request body must be JSON."
        raise InvalidDecisionError(msg) from error


def _paths(body: dict[str, Any]) -> list[str]:
    paths = body.get("paths")
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
        msg = "Body must contain a non-empty list of file 'paths' (strings)."
        raise InvalidDecisionError(msg)
    return paths


async def get_review(request: Request) -> Response:
    from aletheia_mcp.review.service import get_service

    del request
    return JSONResponse(get_service().review_payload())


async def add_to_baseline(request: Request) -> Response:
    from aletheia_mcp.review.service import get_service

    try:
        result = get_service().record_baseline(_paths(await _body(request)))
        return JSONResponse(result)
    except AletheiaError as error:
        return _error_response(error, 500)


async def remove_from_baseline(request: Request) -> Response:
    from aletheia_mcp.review.service import get_service

    try:
        result = get_service().remove_from_baseline(_paths(await _body(request)))
        return JSONResponse(result)
    except AletheiaError as error:
        return _error_response(error, 500)


async def rollback(request: Request) -> Response:
    from aletheia_mcp.review.service import get_service

    try:
        result = get_service().rollback_to_baseline(_paths(await _body(request)))
        return JSONResponse(result)
    except AletheiaError as error:
        status = 500 if isinstance(error, DiskEffectError) else None
        return _error_response(error, status or 500)


async def save_content(request: Request) -> Response:
    from aletheia_mcp.review.service import get_service

    try:
        body = await _body(request)
        path = body.get("path")
        content = body.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            msg = "Body must contain a 'path' and a 'content', both strings."
            raise InvalidDecisionError(msg)
        get_service().write_file_content(path, content)
        return JSONResponse({"path": path, "written": True})
    except AletheiaError as error:
        status = 500 if isinstance(error, DiskEffectError) else None
        return _error_response(error, status or 500)


async def review_page(request: Request) -> Response:
    del request
    index = DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse(FALLBACK_INDEX)


def create_app() -> Starlette:
    routes: list[Any] = [
        Route("/", review_page),
        Route("/api/review", get_review, methods=["GET"]),
        Route("/api/baseline/files", add_to_baseline, methods=["POST"]),
        Route("/api/baseline/files", remove_from_baseline, methods=["DELETE"]),
        Route("/api/rollback", rollback, methods=["POST"]),
        Route("/api/content", save_content, methods=["POST"]),
    ]
    assets = DIST_DIR / "assets"
    if assets.exists():
        routes.append(Mount("/assets", app=StaticFiles(directory=assets), name="assets"))
    return Starlette(routes=routes)
