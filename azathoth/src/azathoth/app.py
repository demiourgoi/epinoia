"""The FastAPI application exposing the OpenAI-compatible chat completions API.

Only requests originating from a loopback address are accepted. Chat
completion requests are forwarded to the ACP agent through the tools-disabled
bridge, and the answer is returned in the OpenAI response format.
"""

import ipaddress
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException

from azathoth.acp_client import AcpBridge, AcpBridgeError, CompletionResult
from azathoth.openai_models import (
    ChatCompletionRequest,
    acp_stop_reason_to_finish_reason,
    build_completion,
    build_stream_chunks,
    error_body,
)
from azathoth.settings import Settings

_LOOPBACK_MSG = "azathoth only accepts requests from localhost"


class LoopbackDeniedError(Exception):
    def __init__(self, message: str = _LOOPBACK_MSG) -> None:
        self.message = message
        super().__init__(message)


async def _loopback_guard(request: Request) -> None:
    host = request.client.host if request.client is not None else ""
    if host == "testclient":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise LoopbackDeniedError from exc
    if not address.is_loopback:
        raise LoopbackDeniedError


def _http_error_type(status_code: int) -> str:
    if status_code == 403:
        return "permission_error"
    if 400 <= status_code < 500:
        return "invalid_request_error"
    return "api_error"


def create_app(bridge: AcpBridge) -> FastAPI:
    """Build the app wired to the given bridge (started through its lifespan)."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await bridge.start()
        try:
            yield
        finally:
            await bridge.stop()

    app = FastAPI(title="azathoth", lifespan=lifespan, docs_url=None, openapi_url=None)

    @app.exception_handler(LoopbackDeniedError)
    async def _loopback_denied(_: Request, exc: LoopbackDeniedError) -> JSONResponse:
        return JSONResponse(status_code=403, content=error_body(exc.message, "permission_error").model_dump())

    @app.exception_handler(HTTPException)
    async def _http_error(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(str(exc.detail), _http_error_type(exc.status_code)).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def _invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]["msg"] if exc.errors() else "invalid request"
        return JSONResponse(status_code=400, content=error_body(first, "invalid_request_error").model_dump())

    @app.exception_handler(AcpBridgeError)
    async def _bridge_error(_: Request, exc: AcpBridgeError) -> JSONResponse:
        return JSONResponse(status_code=502, content=error_body(str(exc), "api_error").model_dump())

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content=error_body(str(exc), "api_error").model_dump())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/chat/completions", response_model=None, dependencies=[Depends(_loopback_guard)])
    async def chat_completions(request: ChatCompletionRequest) -> JSONResponse | StreamingResponse:
        result = await bridge.complete(request.model, request.messages, request.max_tokens)
        finish_reason = acp_stop_reason_to_finish_reason(result.stop_reason)
        if request.stream:
            return StreamingResponse(
                _sse_stream(request, result, finish_reason),
                media_type="text/event-stream",
            )
        return JSONResponse(build_completion(request, "".join(result.text_pieces), finish_reason))

    return app


async def _sse_stream(
    request: ChatCompletionRequest, result: CompletionResult, finish_reason: str
) -> AsyncIterator[bytes]:
    for chunk in build_stream_chunks(request, result.text_pieces, finish_reason):
        yield f"data: {json.dumps(chunk)}\n\n".encode()
    yield b"data: [DONE]\n\n"


def run() -> None:
    settings = Settings()
    bridge = AcpBridge([settings.acp_command, *settings.acp_args], timeout_secs=settings.timeout_secs)
    uvicorn.run(create_app(bridge), host=settings.host, port=settings.port, log_level="info")
