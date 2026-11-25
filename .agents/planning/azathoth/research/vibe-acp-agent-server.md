# Research: running the Vibe CLI as an ACP agent server

Sources:

- Mistral docs, "Use Vibe in other IDEs":
  https://docs.mistral.ai/vibe/code/use-vibe-in-other-ides
- Mistral Vibe README: https://github.com/mistralai/mistral-vibe
- ACP registry entry: 
  https://github.com/agentclientprotocol/registry/tree/main/mistral-vibe

## Findings

- Installing the Vibe CLI (`curl -LsSf https://mistral.ai/vibe/install.sh | bash`
  or `uv tool install --python 3.14 mistral-vibe`) also installs the
  `vibe-acp` executable: an ACP agent server speaking protocol v1 over stdio.
- Clients without an agent registry (Zed, Xcode, custom clients) point at the
  `vibe-acp` binary directly; Xcode wants `command -v vibe-acp` as the
  absolute executable.
- Authentication is shared with the Vibe CLI: OAuth login through Mistral AI
  Studio, or `MISTRAL_API_KEY` in the environment; the key is stored in the
  OS keyring or `~/.vibe/.env` and reused.
- `vibe-acp` shares `~/.vibe/` and per-project `.vibe/` configuration
  (agents, skills, MCP servers). A custom agent defined in
  `.vibe/agents/<name>.toml` can therefore disable built-in tools server-side
  (`enabled_tools = []` or explicit `disabled_tools`), mirroring the
  epinoia `.vibe/agents/ponytail-reviewer.toml` pattern.
- The agent announces its `model`, `agent`, `mode`, `thinking`, `max_turns`,
  and `max_tokens` config options in `session/new`, and clients select values
  with `session/set_config_option`.

## Consequence for azathoth

`AZATHOTH_ACP_COMMAND` defaults to `vibe-acp` so the proxy works with a plain
Vibe CLI install; the README documents install + authentication + a
tools-disabled agent TOML. Any other ACP agent (e.g. the SDK's example echo
agent) can be substituted, which is also how the hermetic tests fake the
agent side.
