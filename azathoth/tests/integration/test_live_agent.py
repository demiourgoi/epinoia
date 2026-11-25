"""Live ACP agent round-trip tests.

Skipped by default: set ``AZATHOTH_INTEGRATION_ACP_COMMAND`` to a real ACP
agent server executable (for example ``vibe-acp``) to run them. These tests
perform real model calls and always run from the local host. Extra agent
arguments may be given in ``AZATHOTH_INTEGRATION_ACP_ARGS``.
"""

import os
import shlex

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("AZATHOTH_INTEGRATION_ACP_COMMAND"),
    reason="AZATHOTH_INTEGRATION_ACP_COMMAND is not set; skipping live agent tests",
)


def test_live_agent_completion() -> None:

    from fastapi.testclient import TestClient

    from azathoth.acp_client import AcpBridge
    from azathoth.app import create_app

    command = [
        os.environ["AZATHOTH_INTEGRATION_ACP_COMMAND"],
        *shlex.split(os.environ.get("AZATHOTH_INTEGRATION_ACP_ARGS", "")),
    ]
    bridge = AcpBridge(command, timeout_secs=float(os.environ.get("AZATHOTH_TIMEOUT_SECS", "600")))
    with TestClient(create_app(bridge)) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": os.environ.get("AZATHOTH_INTEGRATION_MODEL", "mistral-small"),
                "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["choices"][0]["message"]["content"].strip()
