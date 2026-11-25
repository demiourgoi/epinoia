# Rough Idea

Implement in Python 3.14 a service that exposes an OpenAI-compatible API for
chat completions only, accepting requests from localhost only, and forwards
each chat request to an ACP agent with all tools disabled, returning the
agent's answer in the expected OpenAI response format. The README must include
instructions for using the Vibe CLI (`vibe-acp`) as the ACP agent server.
FastAPI is the preferred web framework.

Context: the service lives in a new top-level folder `azathoth/` of the
epinoia repository, and is developed following the PDD methodology with all
artifacts in English.

References:

- How to build an OpenAI-compatible API: https://towardsdatascience.com/how-to-build-an-openai-compatible-api-87c8edea2f06/
- ACP Python SDK: https://agentclientprotocol.com/libraries/python
- Pydantic ACP harness: https://pydantic.dev/docs/ai/harness/acp/

Preliminary research provided by the requester (Vibe CLI v3.1.5):

- Vibe depends on `agent-client-protocol==0.11.0`, protocol version 1.
- Vibe ships `vibe-acp`, an ACP agent server usable from any ACP client
  (Zed, Xcode, JetBrains, or a custom client).
- The agent supports sessions, config options (`model`, `agent`, `mode`,
  `thinking`, `max_turns`, `max_tokens`), and MCP servers contributed by the
  client.
