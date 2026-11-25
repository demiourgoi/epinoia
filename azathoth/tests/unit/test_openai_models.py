import pytest
from pydantic import ValidationError

from azathoth.openai_models import (
    build_completion,
    build_stream_chunks,
    error_body,
    flatten_messages,
)


def _request(**overrides):
    body = {"model": "mistral-small", "messages": [{"role": "user", "content": "hello"}]}
    body.update(overrides)
    return body


def test_minimal_request_parses() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    req = ChatCompletionRequest.model_validate(_request())
    assert req.model == "mistral-small"
    assert req.stream is False
    assert req.max_tokens is None


def test_unknown_fields_allowed() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    req = ChatCompletionRequest.model_validate(_request(temperature=0.3, user="abc"))
    assert req.model_extra is not None
    assert req.model_extra["temperature"] == 0.3


def test_missing_model_rejected() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate({"messages": [{"role": "user", "content": "hi"}]})


def test_empty_messages_rejected() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate({"model": "m", "messages": []})


def test_tools_rejected() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    with pytest.raises(ValidationError, match="tools-disabled"):
        ChatCompletionRequest.model_validate(_request(tools=[{"type": "function"}]))


def test_tool_message_rejected() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    with pytest.raises(ValidationError, match="tools-disabled"):
        ChatCompletionRequest.model_validate({"model": "m", "messages": [{"role": "tool", "content": "x"}]})


def test_message_extra_fields_rejected() -> None:
    from azathoth.openai_models import ChatMessage

    with pytest.raises(ValidationError):
        ChatMessage.model_validate({"role": "user", "content": "hi", "name": "x"})


def test_invalid_role_rejected() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate({"model": "m", "messages": [{"role": "robot", "content": "hi"}]})


def test_flatten_single_user_message() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    req = ChatCompletionRequest.model_validate(_request())
    assert flatten_messages(req.messages) == "hello"


def test_flatten_full_history() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    req = ChatCompletionRequest.model_validate({
        "model": "m",
        "messages": [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
            {"role": "user", "content": "second question"},
        ],
    })
    assert flatten_messages(req.messages) == (
        "System instructions: be terse\n\nUser: first question\n\nAssistant: first answer\n\nsecond question"
    )


def test_build_completion_shape() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    req = ChatCompletionRequest.model_validate(_request())
    body = build_completion(req, "hi there", "stop")
    assert body["object"] == "chat.completion"
    assert body["model"] == "mistral-small"
    assert body["id"].startswith("chatcmpl-")
    assert body["choices"][0]["message"] == {"role": "assistant", "content": "hi there"}
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["usage"] == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def test_build_stream_chunks_shape() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    req = ChatCompletionRequest.model_validate(_request())
    chunks = build_stream_chunks(req, ["hi ", "there"], "stop")
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert all(c["id"] == chunks[0]["id"] for c in chunks)
    assert chunks[0]["choices"][0]["delta"] == {"role": "assistant"}
    assert chunks[1]["choices"][0]["delta"] == {"content": "hi "}
    assert chunks[2]["choices"][0]["delta"] == {"content": "there"}
    assert chunks[3]["choices"][0]["finish_reason"] == "stop"


def test_build_stream_chunks_skips_empty_pieces() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    req = ChatCompletionRequest.model_validate(_request())
    chunks = build_stream_chunks(req, ["", "there"], "stop")
    assert [c["choices"][0]["delta"] for c in chunks] == [
        {"role": "assistant"},
        {"content": "there"},
        {},
    ]


def test_error_body_shape() -> None:
    body = error_body("boom", "invalid_request_error", param="model")
    assert body.error.message == "boom"
    assert body.error.type == "invalid_request_error"
    assert body.error.param == "model"
    assert body.error.code is None


def test_stop_reason_mapping() -> None:
    from azathoth.openai_models import acp_stop_reason_to_finish_reason

    assert acp_stop_reason_to_finish_reason("end_turn") == "stop"
    assert acp_stop_reason_to_finish_reason("max_tokens") == "length"
    assert acp_stop_reason_to_finish_reason("refusal") == "content_filter"
    assert acp_stop_reason_to_finish_reason("cancelled") == "stop"


def test_non_user_last_message_rejected() -> None:
    from azathoth.openai_models import ChatCompletionRequest

    with pytest.raises(ValidationError, match="last message"):
        ChatCompletionRequest.model_validate({
            "model": "m",
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        })
