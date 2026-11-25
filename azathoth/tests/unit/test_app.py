import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from azathoth.acp_client import AgentUnavailableError, CompletionResult
from azathoth.app import LoopbackDeniedError, create_app
from azathoth.openai_models import ChatMessage
from azathoth.settings import Settings

FAKE_AGENT = [sys.executable, str(Path(__file__).parent / "fake_agent.py")]


@pytest.fixture
def app():
    from azathoth.acp_client import AcpBridge

    return create_app(AcpBridge(FAKE_AGENT, timeout_secs=10.0))


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_path_returns_openai_404(client):
    response = client.get("/v1/models")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert "message" in body["error"]


def test_non_loopback_client_rejected(app):
    with TestClient(app, client=("10.20.30.40", 1234), raise_server_exceptions=False) as remote:
        response = remote.post(
            "/v1/chat/completions",
            json={"model": "mistral-small", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert response.status_code == 403
    assert response.json()["error"]["type"] == "permission_error"


def test_completion_round_trip(client):
    response = client.post(
        "/v1/chat/completions",
        json={"model": "mistral-small", "messages": [{"role": "user", "content": "hey there"}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "mistral-small"
    assert body["id"].startswith("chatcmpl-")
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert "hey there" in body["choices"][0]["message"]["content"]
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["usage"]["total_tokens"] == 0


def test_multiturn_history_forwarded(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mistral-small",
            "messages": [
                {"role": "system", "content": "be terse"},
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "first answer"},
                {"role": "user", "content": "second question"},
            ],
        },
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "System instructions: be terse" in content
    assert "first answer" in content
    assert "second question" in content
    assert "echo System instructions: be terse" in content


def test_unknown_sampling_fields_accepted(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mistral-small",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.2,
            "top_p": 0.5,
        },
    )
    assert response.status_code == 200


def test_tools_rejected_with_openai_400(client):
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "mistral-small",
            "messages": [{"role": "user", "content": "hi"}],
            "tools": [{"type": "function"}],
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["type"] == "invalid_request_error"
    assert "tools-disabled" in body["error"]["message"]


def test_malformed_body_returns_openai_400(client):
    response = client.post("/v1/chat/completions", json={"messages": []})
    assert response.status_code == 400
    assert response.json()["error"]["type"] == "invalid_request_error"


def test_bridge_failure_returns_502():
    bridge = AsyncMock()
    bridge.complete = AsyncMock(side_effect=AgentUnavailableError("turn failed"))
    broken = create_app(bridge)
    with TestClient(broken, raise_server_exceptions=False) as broken_client:
        response = broken_client.post(
            "/v1/chat/completions",
            json={"model": "mistral-small", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert response.status_code == 502
    assert response.json()["error"]["type"] == "api_error"


def test_permission_denial_surfaces_in_content(client):
    response = client.post(
        "/v1/chat/completions",
        json={"model": "mistral-small", "messages": [{"role": "user", "content": "please PERMISSION"}]},
    )
    assert response.status_code == 200
    assert "cancelled" in response.json()["choices"][0]["message"]["content"]


def test_loopback_guard_allows_testclient():
    from azathoth.app import _loopback_guard

    class FakeRequest:
        client = type("C", (), {"host": "testclient"})()

    import asyncio

    asyncio.run(_loopback_guard(FakeRequest()))


def test_loopback_guard_rejects_non_ip():
    from azathoth.app import _loopback_guard

    class FakeRequest:
        client = type("C", (), {"host": "not-an-ip"})()

    import asyncio

    with pytest.raises(LoopbackDeniedError):
        asyncio.run(_loopback_guard(FakeRequest()))


def test_settings_defaults_reachable():
    settings = Settings()
    assert settings.host == "127.0.0.1"


def test_completion_result_dataclass_defaults():
    result = CompletionResult()
    assert result.text_pieces == []
    assert result.stop_reason == "end_turn"


def test_chat_message_model():
    message = ChatMessage(role="user", content="hi")
    assert message.role == "user"
