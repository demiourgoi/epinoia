# Research: ACP protocol and the Python SDK

Sources:

- ACP specification: https://agentclientprotocol.com/protocol/
- Python SDK docs: https://agentclientprotocol.com/libraries/python and
  https://agentclientprotocol.github.io/python-sdk/
- Python SDK source (client example): 
  https://github.com/agentclientprotocol/python-sdk/blob/main/examples/client.py
- Verified empirically against `agent-client-protocol==1.0.0` (the current
  SDK release; the Vibe CLI pins `==0.11.0` — both implement protocol
  version 1, and the wire surface used by the proxy is identical).

## Findings

- The SDK exposes both sides of ACP: `acp.agent` / `acp.client` async base
  classes, `acp.schema` (generated Pydantic models validating every wire
  payload), `acp.helpers`, and JSON-RPC supervision.
- Client-side flow:
  1. Spawn the agent process; connect via `connect_to_agent(client, stdin, stdout)`
     returning a `ClientSideConnection` (`acp.core`).
  2. `await conn.initialize(protocol_version=PROTOCOL_VERSION,
     client_capabilities=..., client_info=Implementation(...))` — the
     `initialize` response carries the agent's protocol version.
  3. `await conn.new_session(cwd=..., mcp_servers=[...])` →
     `NewSessionResponse(session_id, modes, config_options)`.
  4. `await conn.prompt(session_id, prompt=[TextContentBlock(...)])` →
     `PromptResponse(stop_reason)`.
  5. Streaming content arrives as `session/update` notifications delivered
     to the client's `session_update` callback (`AgentMessageChunk` carries
     text/image/resource content blocks).
- `Client` subclass hooks relevant to disabling tools (verified field layout
  against the installed schema):
  - `request_permission(session_id, tool_call, options) -> RequestPermissionResponse`
    with `RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))`
    as the safe denial; `PermissionOption.kind` is one of
    `allow_once/allow_always/reject_once/reject_always`.
  - `create_elicitation(message, mode)` → return
    `DeclineElicitationResponse(action="decline")`.
  - `write_text_file`, `read_text_file`, `create_terminal`, `terminal_output`,
    `release_terminal`, `wait_for_terminal_exit`, `kill_terminal` → raising
    `RequestError.method_not_found(<method>)` makes the JSON-RPC layer
    respond with a method-not-found error to the agent.
- `NewSessionRequest(cwd, additional_directories, mcp_servers, _meta)`:
  passing `mcp_servers=[]` contributes no client tools.
- `PromptResponse` carries only `stop_reason` — final text must be
  accumulated from `AgentMessageChunk` updates, which is exactly what the
  streaming and non-streaming paths both need. `StopReason` values:
  `end_turn, max_tokens, max_turn_requests, refusal, cancelled` — they map
  cleanly onto OpenAI `finish_reason` (`end_turn`/`refusal`/`cancelled` →
  `stop` or `content_filter`, `max_tokens` → `length`).
- Config options (`session/set_config_option`) are how model/agent/mode are
  selected in a server-agnostic way; Vibe advertises `model`, `agent`,
  `mode`, `thinking`, `max_turns`, `max_tokens` (requester's research).
- Concurrency: one connection multiplexes multiple sessions; JSON-RPC
  request ids keep responses demultiplexed. Our per-request sessions are
  safe over a single shared connection.

## Consequence for azathoth

The proxy is a pure ACP *client*: it spawns `vibe-acp` (or any ACP agent
binary), keeps one connection, opens a session per chat request, enforces
the no-tools policy through the client hooks above, and folds
`AgentMessageChunk` text blocks into the OpenAI response body or SSE chunks.
