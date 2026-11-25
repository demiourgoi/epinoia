"""ACP client bridge: talks to an ACP agent with every tool channel disabled.

The bridge owns the agent subprocess and one protocol connection. Each chat
completion request gets a fresh ACP session; the tools-disabled policy is
enforced from the client side of the protocol:

- sessions are created without MCP servers;
- permission requests are always denied;
- elicitation requests are always declined;
- file and terminal requests are answered with method-not-found.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from acp import PROTOCOL_VERSION, Client, RequestError, connect_to_agent
from acp.core import ClientSideConnection
from acp.schema import (
    AgentMessageChunk,
    AgentPlanContentUpdate,
    AgentPlanRemovedUpdate,
    AgentPlanUpdate,
    AgentThoughtChunk,
    AvailableCommandsUpdate,
    ClientCapabilities,
    ConfigOptionUpdate,
    ConnectMcpResponse,
    CreateElicitationResponse,
    CreateTerminalResponse,
    CurrentModeUpdate,
    DeclineElicitationResponse,
    DeniedOutcome,
    DisconnectMcpResponse,
    ElicitationMode,
    EnvVariable,
    Implementation,
    KillTerminalResponse,
    NewSessionResponse,
    PermissionOption,
    PromptResponse,
    ReadTextFileResponse,
    ReleaseTerminalResponse,
    RequestPermissionResponse,
    SessionInfoUpdate,
    SessionUpdateCompactionSummaryChunk,
    SessionUpdateCompactionUpdate,
    SessionUpdateNotice,
    TerminalOutputResponse,
    TextContentBlock,
    ToolCallProgress,
    ToolCallStart,
    ToolCallUpdate,
    UsageUpdate,
    UserMessageChunk,
    WaitForTerminalExitResponse,
    WriteTextFileResponse,
)

from azathoth.openai_models import ChatMessage, flatten_messages

logger = logging.getLogger(__name__)

SessionUpdate = (
    UserMessageChunk
    | AgentMessageChunk
    | AgentThoughtChunk
    | ToolCallStart
    | ToolCallProgress
    | AgentPlanUpdate
    | AgentPlanContentUpdate
    | AgentPlanRemovedUpdate
    | AvailableCommandsUpdate
    | CurrentModeUpdate
    | ConfigOptionUpdate
    | SessionInfoUpdate
    | UsageUpdate
    | SessionUpdateNotice
    | SessionUpdateCompactionUpdate
    | SessionUpdateCompactionSummaryChunk
)


class AcpBridgeError(Exception):
    """Base error for bridge failures surfaced as OpenAI api_error."""


class AgentUnavailableError(AcpBridgeError):
    """The agent process could not be started or answered the handshake."""


class AgentTimeoutError(AcpBridgeError):
    """The agent turn exceeded AZATHOTH_TIMEOUT_SECS."""


@dataclass
class CompletionResult:
    """The agent's answer to one chat completion request."""

    text_pieces: list[str] = field(default_factory=list)
    stop_reason: str = "end_turn"


@dataclass
class PieceEvent:
    """A text fragment streamed by the agent mid-turn."""

    text: str


@dataclass
class StopEvent:
    """The final stop reason of a streamed turn."""

    stop_reason: str


StreamEvent = PieceEvent | StopEvent


class ToolsDisabledClient(Client):
    """Client hooks implementing the tools-disabled policy and update routing."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[SessionUpdate]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue[SessionUpdate]:
        queue: asyncio.Queue[SessionUpdate] = asyncio.Queue()
        self._queues[session_id] = queue
        return queue

    def unsubscribe(self, session_id: str) -> None:
        self._queues.pop(session_id, None)

    async def request_permission(
        self, session_id: str, tool_call: ToolCallUpdate, options: list[PermissionOption], **kwargs: object
    ) -> RequestPermissionResponse:
        logger.warning("denying permission request for tool %r in session %s", tool_call.name, session_id)
        return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))

    async def create_elicitation(
        self, message: str, mode: ElicitationMode, **kwargs: object
    ) -> CreateElicitationResponse:
        logger.warning("declining elicitation request: %s", message)
        return DeclineElicitationResponse(action="decline")

    async def complete_elicitation(self, elicitation_id: str, **kwargs: object) -> None:
        return None

    async def write_text_file(
        self, session_id: str, path: str, content: str, **kwargs: object
    ) -> WriteTextFileResponse:
        raise RequestError.method_not_found("fs/write_text_file")

    async def read_text_file(
        self, session_id: str, path: str, line: int | None = None, limit: int | None = None, **kwargs: object
    ) -> ReadTextFileResponse:
        raise RequestError.method_not_found("fs/read_text_file")

    async def create_terminal(
        self,
        session_id: str,
        command: str,
        args: list[str] | None = None,
        env: list[EnvVariable] | None = None,
        cwd: str | None = None,
        output_byte_limit: int | None = None,
        **kwargs: object,
    ) -> CreateTerminalResponse:
        raise RequestError.method_not_found("terminal/create")

    async def terminal_output(self, session_id: str, terminal_id: str, **kwargs: object) -> TerminalOutputResponse:
        raise RequestError.method_not_found("terminal/output")

    async def release_terminal(
        self, session_id: str, terminal_id: str, **kwargs: object
    ) -> ReleaseTerminalResponse | None:
        raise RequestError.method_not_found("terminal/release")

    async def wait_for_terminal_exit(
        self, session_id: str, terminal_id: str, **kwargs: object
    ) -> WaitForTerminalExitResponse:
        raise RequestError.method_not_found("terminal/wait_for_exit")

    async def kill_terminal(self, session_id: str, terminal_id: str, **kwargs: object) -> KillTerminalResponse | None:
        raise RequestError.method_not_found("terminal/kill")

    def on_connect(self, conn: object) -> None:
        return None

    async def connect_mcp(self, server_id: str, **kwargs: object) -> ConnectMcpResponse:
        raise RequestError.method_not_found("mcp/connect")

    async def disconnect_mcp(self, connection_id: str, **kwargs: object) -> DisconnectMcpResponse:
        raise RequestError.method_not_found("mcp/disconnect")

    async def mcp_message(
        self, connection_id: str, method: str, params: dict | None = None, **kwargs: object
    ) -> object:
        raise RequestError.method_not_found("mcp/message")

    async def notify_mcp(self, connection_id: str, method: str, params: dict | None = None, **kwargs: object) -> None:
        return None

    async def session_update(self, session_id: str, update: SessionUpdate, **kwargs: object) -> None:
        queue = self._queues.get(session_id)
        if queue is not None:
            await queue.put(update)

    async def ext_method(self, method: str, params: dict) -> dict:
        raise RequestError.method_not_found(method)

    async def ext_notification(self, method: str, params: dict) -> None:
        return None


class AcpBridge:
    """One agent subprocess, one connection, one session per request."""

    def __init__(self, command: list[str], *, timeout_secs: float = 600.0) -> None:
        self._command = command
        self._timeout_secs = timeout_secs
        self._client = ToolsDisabledClient()
        self._proc: asyncio.subprocess.Process | None = None
        self._connection: ClientSideConnection | None = None
        self._connect_lock = asyncio.Lock()

    async def start(self) -> None:
        await self._connect()

    async def stop(self) -> None:
        await self._terminate()

    async def complete(self, model: str, messages: list[ChatMessage], max_tokens: int | None) -> CompletionResult:
        """Run one chat request through a fresh ACP session."""
        try:
            return await asyncio.wait_for(self._complete(model, messages, max_tokens), timeout=self._timeout_secs)
        except TimeoutError as exc:
            await self._after_failure()
            raise AgentTimeoutError("agent turn timed out") from exc
        except RequestError as exc:
            raise AcpBridgeError(f"agent turn failed: {exc}") from exc

    async def stream(
        self, model: str, messages: list[ChatMessage], max_tokens: int | None
    ) -> AsyncIterator[StreamEvent]:
        """Yield the agent's answer piece by piece, then a StopEvent."""
        async with self._connect_lock:
            if self._connection is None or (self._proc is not None and self._proc.returncode is not None):
                await self._connect()
            connection = self._connection
        if connection is None:
            raise AgentUnavailableError("agent connection is not established")
        session = await connection.new_session(cwd=str(Path.cwd()), mcp_servers=[])
        queue = self._client.subscribe(session.session_id)
        try:
            await self._apply_config_options(connection, session, model=model, max_tokens=max_tokens)
            prompt = flatten_messages(messages)
            prompt_task = asyncio.create_task(
                asyncio.wait_for(
                    connection.prompt(session_id=session.session_id, prompt=[TextContentBlock(text=prompt)]),
                    timeout=self._timeout_secs,
                )
            )
            try:
                async for event in self._pump(queue, prompt_task):
                    yield event
            finally:
                prompt_task.cancel()
        except TimeoutError as exc:
            await self._after_failure()
            raise AgentTimeoutError("agent turn timed out") from exc
        except RequestError as exc:
            raise AcpBridgeError(f"agent turn failed: {exc}") from exc
        finally:
            self._client.unsubscribe(session.session_id)

    @staticmethod
    async def _pump(
        queue: asyncio.Queue[SessionUpdate], prompt_task: asyncio.Task[PromptResponse]
    ) -> AsyncIterator[StreamEvent]:
        while True:
            get_task = asyncio.create_task(queue.get())
            done, _pending = await asyncio.wait({prompt_task, get_task}, return_when=asyncio.FIRST_COMPLETED)
            if get_task in done:
                text = _message_text(get_task.result())
                if text is not None:
                    yield PieceEvent(text=text)
            if prompt_task in done:
                try:
                    while not queue.empty():
                        text = _message_text(queue.get_nowait())
                        if text is not None:
                            yield PieceEvent(text=text)
                finally:
                    get_task.cancel()
                response = prompt_task.result()
                yield StopEvent(stop_reason=response.stop_reason)
                return

    async def _complete(self, model: str, messages: list[ChatMessage], max_tokens: int | None) -> CompletionResult:
        async with self._connect_lock:
            if self._connection is None or (self._proc is not None and self._proc.returncode is not None):
                await self._connect()
            connection = self._connection
        if connection is None:
            raise AgentUnavailableError("agent connection is not established")
        session = await connection.new_session(cwd=str(Path.cwd()), mcp_servers=[])
        queue = self._client.subscribe(session.session_id)
        try:
            await self._apply_config_options(connection, session, model=model, max_tokens=max_tokens)
            prompt = flatten_messages(messages)
            response = await connection.prompt(session_id=session.session_id, prompt=[TextContentBlock(text=prompt)])
            result = CompletionResult(
                text_pieces=_extract_pieces(queue),
                stop_reason=response.stop_reason,
            )
        finally:
            self._client.unsubscribe(session.session_id)
        return result

    async def _apply_config_options(
        self,
        connection: ClientSideConnection,
        session: NewSessionResponse,
        *,
        model: str,
        max_tokens: int | None,
    ) -> None:
        for option in session.config_options or []:
            if option.id == "model" and _select_has_value(option, model):
                await connection.set_config_option(config_id="model", session_id=session.session_id, value=model)
            elif option.id == "max_tokens" and max_tokens is not None and _select_has_value(option, str(max_tokens)):
                await connection.set_config_option(
                    config_id="max_tokens", session_id=session.session_id, value=str(max_tokens)
                )

    async def _connect(self) -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                *self._command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
            )
        except (OSError, FileNotFoundError) as exc:
            raise AgentUnavailableError(f"could not start agent process: {exc}") from exc
        if proc.stdin is None or proc.stdout is None:
            raise AgentUnavailableError("agent process does not expose stdio pipes")
        connection = connect_to_agent(self._client, proc.stdin, proc.stdout)
        try:
            await connection.initialize(
                protocol_version=PROTOCOL_VERSION,
                client_capabilities=ClientCapabilities(),
                client_info=Implementation(name="azathoth", title="Azathoth", version="0.1.0"),
            )
        except (RequestError, EOFError, asyncio.IncompleteReadError) as exc:
            proc.terminate()
            with contextlib.suppress(ProcessLookupError):
                await proc.wait()
            raise AgentUnavailableError(f"agent handshake failed: {exc}") from exc
        await self._terminate()
        self._proc = proc
        self._connection = connection

    async def _after_failure(self) -> None:
        await self._terminate()
        self._connection = None

    async def _terminate(self) -> None:
        if self._proc is not None and self._proc.returncode is None:
            self._proc.terminate()
            with contextlib.suppress(ProcessLookupError):
                await self._proc.wait()
        self._proc = None
        self._connection = None


def _message_text(update: SessionUpdate) -> str | None:
    if isinstance(update, AgentMessageChunk) and isinstance(update.content, TextContentBlock):
        return update.content.text
    return None


def _extract_pieces(queue: asyncio.Queue[SessionUpdate]) -> list[str]:
    pieces: list[str] = []
    while not queue.empty():
        text = _message_text(queue.get_nowait())
        if text is not None:
            pieces.append(text)
    return pieces


def _select_has_value(option: object, value: str) -> bool:
    options = getattr(option, "options", None)
    if not options:
        return False
    return any(getattr(item, "value", None) == value for item in options)
