# Idea Honing

This task is executed fully unattended, so no interactive Q&A rounds were
possible. Decisions below were taken by the implementing agent using the
requirements, the requester's preliminary research, and best judgement, and
are recorded in the question/answer format the PDD process prescribes.

## Q1: Which endpoints must the OpenAI-compatible API expose?

**Answer:** Only `POST /v1/chat/completions`. No models endpoint, no
embeddings, no legacy `/v1/completions`. The response must follow the
OpenAI chat completion schema (id, object, created, model, choices with
message, finish_reason, usage). Unsupported OpenAI fields are accepted and
ignored where harmless, or rejected with an OpenAI-style JSON error when
they cannot be honored.

## Q2: Should streaming (`"stream": true`) be supported?

**Answer:** Yes. Many OpenAI client libraries default to streaming; refusing
them would make the proxy unusable with common tools. Streaming uses the
ACP `session/update` `AgentMessageChunk` notifications and emits
`chat.completion.chunk` SSE events, terminated by a `data: [DONE]` sentinel.

## Q3: How is "localhost only" enforced?

**Answer:** In two layers. (1) The server binds only to `127.0.0.1` by
default (`AZATHOTH_HOST`, default `127.0.0.1`; binding to `0.0.0.0` requires
an explicit override by the operator). (2) An application-level guard
rejects any request whose client address is not a loopback address with a
`403` OpenAI-style error, so the service stays safe even if it is ever run
behind a proxy or with a non-default bind address.

## Q4: How are "all tools disabled" enforced on the ACP agent?

**Answer:** Defense in depth, from the client side of ACP (the proxy is the
client, so it controls every tool channel the protocol defines):

- `session/new` is created with `mcp_servers: []`: no client-contributed
  MCP servers, so no MCP tools.
- `session/request_permission` is always answered with a denied outcome:
  any agent-side tool that needs approval is refused.
- Elicitation requests (`session/elicitation`) are always declined, so the
  agent cannot obtain new information or credentials interactively.
- `fs/write_text_file`, `fs/read_text_file`, and all `terminal/*` client
  methods respond with JSON-RPC method-not-found errors, so the agent
  cannot read or write files or run commands through the client.

The README also documents how to run `vibe-acp` against a `.vibe` agent
definition with all built-in tools disabled (`enabled_tools = []` /
`disabled_tools`), giving a server-side belt to the client-side suspenders.

## Q5: How is chat state handled? ACP sessions are stateful, the chat completions API is stateless.

**Answer:** Each chat completion request gets a fresh ACP session on a
long-lived connection to the agent process. The full OpenAI `messages` array
is flattened into a single ACP prompt: the system message becomes a
`SystemMessage`-labeled prelude, and prior user/assistant turns are rendered
as a labeled transcript followed by the new user message. This keeps the
proxy stateless, simple, and correct for typical OpenAI clients, at the cost
of re-sending history on each request. Session-per-request also avoids
cross-request context leakage.

## Q6: How is the ACP agent process managed?

**Answer:** The FastAPI lifespan starts the agent server as a child process
(`AZATHOTH_ACP_COMMAND`, default `vibe-acp`, overridable arg/env list), keeps
one connection for the lifetime of the service, and creates one ACP session
per request. If the agent process dies, the connection is re-established
lazily on the next request.

## Q7: Python and dependency choices?

**Answer:** Python 3.14 (the project's `requires-python` is `>=3.14`, matching
the Vibe CLI's own runtime). FastAPI + uvicorn for HTTP, and the official
`agent-client-protocol` Python SDK for the ACP side. Tests use pytest plus
FastAPI's TestClient; ACP is exercised against a scripted in-process fake
agent built on the same SDK's agent-side classes, so tests stay hermetic
(the repo convention: `make test` must not touch the network or spend
tokens).

## Q8: Where do the code and tests live?

**Answer:** Code in `azathoth/` (a Python package + `pyproject.toml` +
`README.md`), tests in `azathoth/tests/`, runnable with `uv run pytest` from
the folder. The repository's existing shell-based test suites are observed
for other features; the azathoth tests are hermetic Python tests.

## Q9: Model selection and parameters (`model`, `temperature`, ...)?

**Answer:** The `model` field is echoed back in the response (as OpenAI
clients expect) and, when the ACP agent advertises a `model` config option
whose options include the requested alias, the proxy selects it before the
first prompt. Parameters with no ACP mapping (`temperature`, `top_p`,
`presence_penalty`, ...) are ignored. `max_tokens` is translated to the
`max_tokens` config option when advertised.
