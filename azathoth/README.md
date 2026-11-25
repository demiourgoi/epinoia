# Azathoth

A **localhost-only**, **OpenAI-compatible chat completions** proxy backed by
an **ACP agent with all tools disabled**.

Azathoth speaks the OpenAI `/v1/chat/completions` wire format on one side
(JSON and SSE streaming), and the Agent Client Protocol (ACP) on the other,
forwarding each chat request to an ACP agent server — by default
[`vibe-acp`](https://docs.mistral.ai/vibe/code/use-vibe-in-other-ides), the
agent server shipped with the Mistral Vibe CLI — while preventing the agent
from using **any** tools:

- ACP sessions are created with no MCP servers contributed by the client;
- every `session/request_permission` request from the agent is denied;
- every elicitation request is declined;
- `fs/write_text_file`, `fs/read_text_file` and all `terminal/*` client
  requests are answered with JSON-RPC method-not-found.

The agent can therefore only converse. Requests containing `tools`,
`tool_choice`, `functions`, `function_call` or `tool`-role messages are
rejected with an OpenAI `400` error.

## Requirements

- Python 3.14 (uv installs it automatically)
- [uv](https://docs.astral.sh/uv/)
- An ACP agent server — see [Vibe CLI as the ACP agent server](#vibe-cli-as-the-acp-agent-server)

## Install

```bash
cd azathoth
make install     # uv sync, creating .venv on Python 3.14
```

## Run

```bash
make run         # serves http://127.0.0.1:8000
```

or directly:

```bash
uv run azathoth
```

### Configuration

All settings come from `AZATHOTH_*` environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AZATHOTH_HOST` | `127.0.0.1` | Bind address. Keep it loopback; non-loopback addresses are still rejected per request. |
| `AZATHOTH_PORT` | `8000` | Bind port. |
| `AZATHOTH_ACP_COMMAND` | `vibe-acp` | The ACP agent server executable. |
| `AZATHOTH_ACP_ARGS` | *(empty)* | Arguments for the agent server: a JSON list (`'["--flag", "value"]'`) or a space-separated string. |
| `AZATHOTH_TIMEOUT_SECS` | `600` | Seconds to wait for one agent turn; on timeout the request fails and the connection is reopened. |

### Localhost-only enforcement

Two layers: the server binds `127.0.0.1` by default, and every request's
client address is checked (loopback only) before the body is even parsed —
non-loopback clients receive an OpenAI-shaped `403 permission_error`, even
if the server is ever launched behind a proxy or with a different host.

## Using the API

Chat completions work with any OpenAI client pointed at
`http://127.0.0.1:8000/v1`:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="not-needed")
completion = client.chat.completions.create(
    model="mistral-small",
    messages=[{"role": "user", "content": "Say hi"}],
)
print(completion.choices[0].message.content)
```

With plain HTTP (non-streaming, then streaming):

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model": "mistral-small", "messages": [{"role": "user", "content": "Say hi"}]}'

curl -sN http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model": "mistral-small", "messages": [{"role": "user", "content": "Say hi"}], "stream": true}'
```

Note: `model` is echoed in the response and, when the agent advertises a
`model` config option containing the requested value, it is selected on the
agent before prompting. Sampling parameters (`temperature`, `top_p`, ...) are
accepted and ignored. Conversation history is sent as a labeled transcript
(one fresh ACP session per request), so the proxy stays stateless.

## Vibe CLI as the ACP agent server

Azathoth defaults to `vibe-acp`, the ACP agent server installed by the
[Mistral Vibe CLI](https://docs.mistral.ai/vibe/code/overview):

1. **Install the Vibe CLI** (macOS/Linux; on Windows use `uv tool install
   --python 3.14 mistral-vibe`):

   ```bash
   curl -LsSf https://mistral.ai/vibe/install.sh | bash
   # or, with uv:
   uv tool install --python 3.14 mistral-vibe
   ```

2. **Authenticate** — run `vibe` once in your project and sign in with your
   Mistral account, or export `MISTRAL_API_KEY`. The credentials are stored
   by the CLI and reused by `vibe-acp`.

3. **Check the agent server is on PATH**:

   ```bash
   command -v vibe-acp
   ```

4. **Point azathoth at it** — nothing to configure: `AZATHOTH_ACP_COMMAND`
   defaults to `vibe-acp`. For an explicit path or a different agent server:

   ```bash
   AZATHOTH_ACP_COMMAND=/absolute/path/to/vibe-acp make run
   ```

### Recommended: a tools-disabled Vibe agent (server side)

The proxy already disables every tool channel from the client side. For
defense in depth, also run the agent server on a Vibe agent profile with all
built-in tools disabled. Create `.vibe/agents/azathoth.toml` in the
directory where you start azathoth:

```toml
# A Vibe agent that cannot use any tool: pure conversation.
name = "azathoth"
active_model = "default"

# Disable every built-in tool: no shell, no file edits, no MCP.
[tools]
enabled_tools = []
```

Then have the README's default calls select that agent (Vibe advertises an
`agent` config option; azathoth selects the `model` option automatically —
pick the agent profile in the config when both are available), or simply
start azathoth in a directory whose `.vibe/` configuration only defines this
agent.

## Development

```bash
make check           # ruff + mypy + deptry + lockfile check
make test            # hermetic unit tests (no network, no tokens)
make test-integration # live agent round trip; see below
```

Unit tests run against a scripted fake ACP agent (`tests/unit/fake_agent.py`
spawned over stdio), so they never need the real Vibe CLI. Integration tests
(`tests/integration/`) are skipped unless you opt in:

```bash
AZATHOTH_INTEGRATION_ACP_COMMAND=vibe-acp make test-integration
```

## Design and PDD artifacts

This service was developed with the Prompt-Driven Development workflow; the
requirements, research, design and per-step implementation notes live in
[`.agents/planning/azathoth/`](../.agents/planning/azathoth/) in the
repository root.

## License

Original content, licensed under the MIT License — see the repository
[LICENSE](../LICENSE).
