"""A scripted ACP agent used by the hermetic unit tests.

Behaviors (triggered by words in the prompt):

- ``PERMISSION``: asks the client for tool permission, then reports the
  outcome in its reply.
- ``USE_FILE``: tries to write a file through the client, then reports the
  outcome in its reply.
- ``STALL``: never answers (drives the timeout path).
- otherwise: replies with ``hello world`` followed by the transcript and the
  model selected for the session.

The agent advertises a ``model`` config option so the bridge can select
between ``mistral-small`` and ``other-model``; it echoes the selected model in
every reply.
"""

import asyncio
import sys

from acp import Agent, RequestError
from acp.core import AgentSideConnection, run_agent
from acp.schema import (
    AgentCapabilities,
    AgentMessageChunk,
    Implementation,
    InitializeResponse,
    NewSessionResponse,
    PromptResponse,
    SessionConfigOptionSelect,
    SessionConfigSelectOption,
    SetSessionConfigOptionResponse,
    TextContentBlock,
    ToolCallUpdate,
)


class FakeAgent(Agent):
    def __init__(self, conn: AgentSideConnection) -> None:
        self._conn = conn
        self._models = ["mistral-small", "other-model"]
        self._selected: dict[str, str] = {}
        self._session_counter = 0

    async def initialize(self, protocol_version: int, **kwargs: object) -> InitializeResponse:
        return InitializeResponse(
            protocol_version=protocol_version,
            agent_capabilities=AgentCapabilities(fs=False, terminals=False),
            agent_info=Implementation(name="fake-agent", title="Fake Agent", version="0.1.0"),
        )

    async def new_session(self, cwd: str, **kwargs: object) -> NewSessionResponse:
        self._session_counter += 1
        session_id = f"sess-{self._session_counter}"
        self._selected[session_id] = "mistral-small"
        return NewSessionResponse(
            session_id=session_id,
            config_options=[
                SessionConfigOptionSelect(
                    id="model",
                    name="Model",
                    current_value="mistral-small",
                    options=[SessionConfigSelectOption(value=m, name=m) for m in self._models],
                )
            ],
        )

    async def set_config_option(
        self, config_id: str, session_id: str, value: str | bool, **kwargs: object
    ) -> SetSessionConfigOptionResponse:
        if config_id == "model" and isinstance(value, str) and value in self._models:
            self._selected[session_id] = value
        return SetSessionConfigOptionResponse(config_options=[])

    async def prompt(self, session_id: str, prompt: list[TextContentBlock], **kwargs: object) -> PromptResponse:
        text = prompt[0].text if prompt and isinstance(prompt[0], TextContentBlock) else ""
        model = self._selected.get(session_id, "mistral-small")
        if "STALL" in text:
            await asyncio.sleep(30)
            return PromptResponse(stop_reason="end_turn")
        if "PERMISSION" in text:
            update = ToolCallUpdate(tool_call_id="tc-1", title="run shell", name="shell")
            response = await self._conn.request_permission(session_id, update, [])
            outcome = getattr(response.outcome, "outcome", "unknown")
            await self._reply(session_id, f"permission {outcome}")
            return PromptResponse(stop_reason="end_turn")
        if "USE_FILE" in text:
            try:
                await self._conn.write_text_file(session_id, "x.txt", "x")
            except RequestError as exc:
                await self._reply(session_id, f"write failed: {exc}")
            else:
                await self._reply(session_id, "write unexpectedly succeeded")
            return PromptResponse(stop_reason="end_turn")
        await self._reply(session_id, f"hello from {model} and ")
        await self._reply(session_id, f"echo {text}")
        return PromptResponse(stop_reason="end_turn")

    async def _reply(self, session_id: str, text: str) -> None:
        await self._conn.session_update(session_id, AgentMessageChunk(content=TextContentBlock(text=text)))


def main() -> None:
    asyncio.run(run_agent(lambda conn: FakeAgent(conn)))


if __name__ == "__main__":
    sys.exit(main())
