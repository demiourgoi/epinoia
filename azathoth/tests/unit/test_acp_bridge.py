import sys
from pathlib import Path

import pytest

from azathoth.acp_client import AcpBridge, AgentTimeoutError
from azathoth.openai_models import ChatMessage

FAKE_AGENT = [sys.executable, str(Path(__file__).parent / "fake_agent.py")]


@pytest.fixture
def bridge():
    return AcpBridge(FAKE_AGENT, timeout_secs=10.0)


def _user_message(content):
    return [ChatMessage(role="user", content=content)]


async def test_complete_returns_text_pieces_and_stop_reason(bridge):
    await bridge.start()
    try:
        result = await bridge.complete("mistral-small", _user_message("hi there"), None)
        assert result.text_pieces == ["hello from mistral-small and ", "echo hi there"]
        assert result.stop_reason == "end_turn"
    finally:
        await bridge.stop()


async def test_complete_selects_model_config_option(bridge):
    await bridge.start()
    try:
        result = await bridge.complete("other-model", _user_message("hi"), None)
        assert result.text_pieces == ["hello from other-model and ", "echo hi"]
    finally:
        await bridge.stop()


async def test_permission_request_is_denied(bridge):
    await bridge.start()
    try:
        result = await bridge.complete("mistral-small", _user_message("run PERMISSION now"), None)
        assert result.text_pieces == ["permission cancelled"]
    finally:
        await bridge.stop()


async def test_file_access_returns_method_not_found(bridge):
    await bridge.start()
    try:
        result = await bridge.complete("mistral-small", _user_message("please USE_FILE"), None)
        assert any("write failed:" in piece for piece in result.text_pieces)
    finally:
        await bridge.stop()


async def test_timeout_reopens_connection():
    bridge = AcpBridge(FAKE_AGENT, timeout_secs=1.0)
    await bridge.start()
    try:
        with pytest.raises(AgentTimeoutError):
            await bridge.complete("mistral-small", _user_message("STALL for a while"), None)
        result = await bridge.complete("mistral-small", _user_message("back online"), None)
        assert result.text_pieces[0] == "hello from mistral-small and "
    finally:
        await bridge.stop()


async def test_unknown_command_raises_agent_unavailable():
    bridge = AcpBridge(["azathoth-definitely-missing-binary"], timeout_secs=1.0)
    from azathoth.acp_client import AgentUnavailableError

    with pytest.raises(AgentUnavailableError):
        await bridge.start()
