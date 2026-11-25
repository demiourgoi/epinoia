# Azathoth — Implementation Plan

## Checklist

- [ ] Step 1: Project scaffold (pyproject, settings, Makefile, lint gates)
- [ ] Step 2: OpenAI wire models and error handlers
- [ ] Step 3: ACP bridge with tools disabled, fake-agent unit tests
- [ ] Step 4: FastAPI app — routes, loopback guard, lifespan
- [ ] Step 5: Streaming SSE path end-to-end
- [ ] Step 6: README (vibe-acp instructions) and integration test hook

## Working agreements

Proceed step by step:

- After each step, ask me for confirmation before completing it
- When completing a step, add an "Implementation notes" subsection to its section in the plan, summarizing what we did, focusing on deviations from the plan, why we made them, and implications for subsequent steps

Additional working agreements for this repo:

- This task runs unattended: "confirmation" is granted by the review
  process below instead of a human. After each step, a ponytail-style
  review of the step's diff is performed (up to 3 rounds overall across the
  task, stopping early on a "ship it" verdict); blocking findings are fixed
  before the next step, and non-blocking ones are recorded here.
- Build commands: `make install && make check` and `make test` run from
  `azathoth/`. Tests must stay hermetic (no network, no tokens).
- One commit per step, focused diffs only.
- Every artifact and comment in English (per the task's constraints);
  repo code carries no superfluous comments.

## Step 1: Project scaffold

**Objective:** create the `azathoth/` uv project skeleton so every later step
has runnable quality gates.

- `pyproject.toml` following the harold-mcp reference: package name
  `azathoth`, `requires-python = ">=3.14,<3.15"`, `src/azathoth/` layout,
  hatchling build, runtime deps (fastapi, uvicorn, agent-client-protocol,
  pydantic-settings), dev group (pytest, ruff, mypy, deptry), ruff/mypy/
  pytest config blocks, `.python-version` (`3.14`), `.gitignore`, `Makefile`
  with `install/check/test/test-unit/test-integration/run`.
- `src/azathoth/__init__.py` with package docstring and version export.
- `src/azathoth/settings.py`: `Settings(BaseSettings)` with
  `AZATHOTH_`-prefixed fields (host, port, acp_command, acp_args,
  timeout_secs).
- A trivial unit test proving pytest runs and settings defaults load.

**Tests required:** unit test asserting `Settings()` defaults and env-var
override.

**Integration:** none yet; `make check` must pass with an empty package.

**Demo:** `cd azathoth && make install && make check && make test-unit` all
green on Python 3.14.

## Step 2: OpenAI wire models and error handlers

**Objective:** validate chat completion requests and produce exact OpenAI
response payloads, independent of HTTP.

- `src/azathoth/openai_models.py`:
  - `ChatMessage` (`role`, `content: str`), `ChatCompletionRequest`
    (`model`, `messages` non-empty, `stream`, `max_tokens`, model_config
    allowing extras).
  - `build_completion(request, text, finish_reason, usage)` →
    `chat.completion` payload; `build_chunk(...)` → `chat.completion.chunk`
    payload for the SSE path.
  - `error_body(message, error_type, status)` → OpenAI error object.
  - `flatten_messages(messages)` → single prompt string with a labeled
    transcript prelude (system/assistant/prior-user) ending on the last
    user message; `finish_reason` mapping from ACP `StopReason` values.

**Tests required:** unit tests for defaults and rejected inputs (missing
model, empty messages, `tools` present, invalid role/content type),
`flatten_messages` transcript rendering (with and without history/system),
`build_completion`/`build_chunk` shape (id prefix, object, delta roles,
finish reasons), error body shape.

**Integration:** none; pure functions.

**Demo:** `make test-unit` shows prompt flattening and response builders
working for a sample conversation.

## Step 3: ACP bridge with tools disabled

**Objective:** the core bridge, connecting to an ACP agent and enforcing the
no-tools policy.

- `src/azathoth/acp_client.py`:
  - `ToolsDisabledClient(Client)`: permission denial
    (`RequestPermissionResponse(outcome=DeniedOutcome("cancelled"))`),
    elicitation declined, fs/terminal hooks raising
    `RequestError.method_not_found`, and `session_update` demultiplexing by
    `session_id` into registered per-session asyncio queues; unregistered
    sessions are ignored.
  - `AcpBridge`: `start()` spawns `AZATHOTH_ACP_COMMAND` +
    `AZATHOTH_ACP_ARGS`, initializes with `PROTOCOL_VERSION`, `stop()`
    terminates the child; `complete(request)` runs the new-session →
    config-option selection (model, max_tokens when advertised) → prompt →
    collect flow, guarded by `asyncio.wait_for(timeout)`, raising
    typed errors for spawn/timeout/protocol failures.
  - `acp_stop_reason_to_finish_reason()` mapping.
- Fake agent for tests: a small SDK-agent-based script
  (`tests/unit/fake_agent.py`) started via `sys.executable` that replies
  with canned `AgentMessageChunk`s and emits a permission request when its
  prompt contains a tripwire word, proving denial works.

**Tests required:** unit tests driving the real bridge over stdio against
the fake agent: happy path text/two-chunk accumulation; config options
applied when advertised (fake advertises `model`; assert it was selected);
permission request answered denied and the completion still finishes;
timeout path (fake stalls) fails cleanly and the next request reconnects;
client hooks return method-not-found (assert agent side sees the error
through its request failing).

**Integration:** none (the fake agent is local, hermetic).

**Demo:** a pytest run that sends "hello" to the fake agent and gets the
echoed completion, plus a denial scenario.

## Step 4: FastAPI app — routes, loopback guard, lifespan

**Objective:** join the models and bridge behind the HTTP surface.

- `src/azathoth/app.py`:
  - Lifespan owning the single `AcpBridge`; on startup, spawn; on shutdown,
    stop.
  - Loopback guard dependency: request client host must be loopback
    (`ipaddress.ip_address(host).is_loopback`, tolerant of the test client's
    `testclient` host) else `403 permission_error`.
  - `POST /v1/chat/completions` route; any other OpenAI path returns the
    OpenAI-style `404`.
  - Overridden FastAPI validation-error handler (OpenAI `400`
    `invalid_request_error`); exception handlers for bridge errors (`502`)
    and unexpected exceptions (`500`); all bodies OpenAI-shaped.
  - `run()` reading settings; console entry point `azathoth =
    "azathoth.app:run"`.
- Wire non-streaming flow end to end: request → bridge.complete →
  `build_completion`.

**Tests required:** unit tests through `TestClient`: success round trip
against the fake agent (body shape, model echo, finish_reason, usage zero),
loopback rejection (non-loopback client address fixture), 404 for unknown
paths, malformed bodies → OpenAI 400, bridge spawn failure → 502.

**Integration:** none (fake agent).

**Demo:** run the app with the fake agent as ACP command and `curl` a
completion locally; the JSON response is a valid `chat.completion`.

## Step 5: Streaming SSE path end-to-end

**Objective:** support `"stream": true` clients.

- In `app.py`, when `stream` is set, return a `StreamingResponse`
  (`text/event-stream`) that consumes the per-session update queue directly
  and yields `chat.completion.chunk` SSE events (`role` first, `content`
  deltas, terminal chunk with `finish_reason`, then `data: [DONE]`).
- Bridge gains a streaming mode (`complete_stream`) that yields text
  fragments instead of joining, or `complete()` is generalized to expose the
  queue — choose the smaller change.

**Tests required:** unit tests through `TestClient` (`stream=true`):
SSE content type, first chunk carries the assistant role, deltas arrive as
sent by the fake agent, finish_reason in the final chunk, `[DONE]`
sentinel; non-streaming path still passes (regression).

**Integration:** none.

**Demo:** `curl -N` shows incrementally arriving SSE chunks from the fake
agent.

## Step 6: README and integration-test hook

**Objective:** operator documentation and the opt-in live test path.

- `azathoth/README.md`: what it is, install/run instructions
  (`make install`, `make run`, or entry point `azathoth`), the
  `AZATHOTH_*` settings table, and — required by the task — the Vibe CLI
  instructions: install Vibe (`uv tool install --python 3.14
  mistral-vibe`), authenticate (`vibe` sign-in or `MISTRAL_API_KEY`), find
  `vibe-acp` with `command -v vibe-acp`, point `AZATHOTH_ACP_COMMAND` at
  it, and a tools-disabled `.vibe/agents/*.toml` agent example
  (`enabled_tools = []`) that the README recommends selecting; plus a curl
  example (`stream` and non-stream) and a note on localhost enforcement.
- `tests/integration/test_live_agent.py`: skipped unless
  `AZATHOTH_INTEGRATION_ACP_COMMAND` is set; runs the full round trip
  against a live agent; wired into `make test-integration`.
- REUSE.toml: add the new files to the original-content annotation block;
  `uvx reuse lint` green from the repo root (run if available).

**Tests required:** the integration test must be skipped (not failed) in
the default `make test` run; hermetic suites stay green.

**Demo:** README renders a complete setup story; `make test-integration`
explains how to opt in.
