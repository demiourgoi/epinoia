"""The Starlette app: review GUI static assets + JSON API (loopback only).

The API acts only on paths recorded in the baseline; it never touches
paths outside it. Errors map status codes by domain type.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from aletheia_mcp.errors import (
    AletheiaError,
    DiskEffectError,
    InvalidDecisionError,
    NotInBaselineError,
)

DIST_DIR = Path(__file__).resolve().parent.parent / "webui" / "dist"

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


class LoopbackGuard(BaseHTTPMiddleware):
    """Only this machine's pages may drive the mutating review API.

    The GUI is a loopback service, but any web page in the user's browser
    can POST to a local socket with `no-cors` and a text/plain body that
    we would otherwise parse. Mutating requests must therefore declare
    `application/json` (which `no-cors` cannot) and, when they carry an
    Origin or Referer, it must be loopback.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith("/api/") and request.method in ("POST", "DELETE"):
            problem = _guard_problem(request.headers, request.url.hostname)
            if problem is not None:
                return JSONResponse({"error": problem}, status_code=403)
        return await call_next(request)


def _guard_problem(headers: Headers, request_host: str | None) -> str | None:
    content_type = headers.get("content-type", "")
    if content_type.split(";")[0].strip().lower() != "application/json":
        msg = "Mutating requests must have Content-Type application/json."
        return msg
    for header in ("origin", "referer"):
        value = headers.get(header)
        if not value:
            continue
        host = urlsplit(value).hostname
        if host not in LOOPBACK_HOSTS and host != request_host:
            msg = f"Cross-origin {header} header is not allowed on this loopback API."
            return msg
    return None


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


async def root_page(request: Request) -> Response:
    return RedirectResponse("/review", status_code=307)


def create_app() -> Starlette:
    routes: list[Any] = [
        Route("/", root_page),
        Route("/review", review_page),
        Route("/api/review", get_review, methods=["GET"]),
        Route("/api/baseline/files", add_to_baseline, methods=["POST"]),
        Route("/api/baseline/files", remove_from_baseline, methods=["DELETE"]),
        Route("/api/rollback", rollback, methods=["POST"]),
        Route("/api/content", save_content, methods=["POST"]),
    ]
    assets = DIST_DIR / "assets"
    if assets.exists():
        routes.append(Mount("/assets", app=StaticFiles(directory=assets), name="assets"))
    return Starlette(routes=routes, middleware=[Middleware(LoopbackGuard)])
