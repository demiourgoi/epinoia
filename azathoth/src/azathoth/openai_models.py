"""OpenAI chat completions wire models and mapping helpers.

Pure data translation between the OpenAI chat completions payloads and the
flattened prompt text sent to the ACP agent. No I/O lives here.
"""

import time
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ChatRole = Literal["system", "user", "assistant", "tool"]

_UNSUPPORTED_TOOLS_MSG = "azathoth runs a tools-disabled agent; tool fields and tool messages are not supported"
_LAST_MESSAGE_MSG = "the last message must have role 'user'"

_SYSTEM_LABELS: dict[str, str] = {
    "system": "System instructions",
    "user": "User",
    "assistant": "Assistant",
}


class OpenAIError(BaseModel):
    message: str
    type: str
    param: str | None = None
    code: str | None = None


class OpenAIErrorBody(BaseModel):
    error: OpenAIError


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ChatRole
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    max_tokens: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _reject_unsupported_features(self) -> ChatCompletionRequest:
        for field in ("tools", "tool_choice", "functions", "function_call"):
            if self.model_extra and field in self.model_extra:
                raise ValueError(_UNSUPPORTED_TOOLS_MSG)
        for message in self.messages:
            if message.role == "tool":
                raise ValueError(_UNSUPPORTED_TOOLS_MSG)
        if self.messages[-1].role != "user":
            raise ValueError(_LAST_MESSAGE_MSG)
        return self


def error_body(message: str, error_type: str, *, param: str | None = None, code: str | None = None) -> OpenAIErrorBody:
    return OpenAIErrorBody(error=OpenAIError(message=message, type=error_type, param=param, code=code))


def flatten_messages(messages: list[ChatMessage]) -> str:
    """Render the conversation as a single prompt ending on the last user message."""
    last_user = len(messages) - 1
    history = messages[:last_user]
    final = messages[last_user]
    lines: list[str] = []
    for m in history:
        if not m.content.strip():
            continue
        lines.append(f"{_SYSTEM_LABELS[m.role]}: {m.content.strip()}")
    lines.append(final.content.strip())
    return "\n\n".join(lines)


def new_completion_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"


def build_completion(
    request: ChatCompletionRequest,
    text: str,
    finish_reason: str,
) -> dict[str, object]:
    return {
        "id": new_completion_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def build_role_chunk(request: ChatCompletionRequest, completion_id: str, created: int) -> dict[str, object]:
    return _chunk(request, completion_id, created, delta={"role": "assistant"}, finish_reason=None)


def build_content_chunk(
    request: ChatCompletionRequest, completion_id: str, created: int, piece: str
) -> dict[str, object]:
    return _chunk(request, completion_id, created, delta={"content": piece}, finish_reason=None)


def build_finish_chunk(
    request: ChatCompletionRequest, completion_id: str, created: int, finish_reason: str
) -> dict[str, object]:
    return _chunk(request, completion_id, created, delta={}, finish_reason=finish_reason)


def _chunk(
    request: ChatCompletionRequest,
    completion_id: str,
    created: int,
    *,
    delta: dict[str, str],
    finish_reason: str | None,
) -> dict[str, object]:
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": request.model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def acp_stop_reason_to_finish_reason(stop_reason: str) -> str:
    """Map an ACP StopReason value onto the OpenAI finish_reason vocabulary."""
    if stop_reason == "max_tokens":
        return "length"
    if stop_reason == "refusal":
        return "content_filter"
    return "stop"
