# Azathoth — PDD Summary

## What was built

Azathoth (`azathoth/`) is a localhost-only, OpenAI-compatible **chat
completions** proxy, written in Python 3.14 with FastAPI, that answers each
request by prompting an **ACP agent with all tools disabled** (default
agent server: the Mistral Vibe CLI's `vibe-acp`).

Key properties:

- `POST /v1/chat/completions` only, in the exact OpenAI wire format
  (JSON and SSE streaming, `chat.completion` / `chat.completion.chunk`,
  OpenAI-shaped errors for 400/403/404/500/502).
- Localhost-only, enforced twice: loopback bind by default plus a
  request-level loopback guard.
- Tools disabled client-side across every ACP channel: no client MCP
  servers, permission requests denied, elicitations declined, fs/terminal
  methods not found; `tools`-style OpenAI request fields rejected.
- Configurable via `AZATHOTH_*` env settings; session-per-request keeps the
  proxy stateless; model selection via the agent's `model` config option.
- Project follows the harold-mcp conventions (src layout, pydantic-settings,
  ruff/mypy/pytest/deptry, Makefile, uv on Python 3.14).

## Artifacts created

- `.agents/planning/azathoth/rough-idea.md`
- `.agents/planning/azathoth/idea-honing.md` (unattended decisions)
- `.agents/planning/azathoth/research/` — ACP SDK, OpenAI wire format,
  vibe-acp agent server, project conventions
- `.agents/planning/azathoth/design/detailed-design.md` (+ round-1 review)
- `.agents/planning/azathoth/implementation/plan.md` (checklist, working
  agreements, per-step implementation notes)
- `.agents/planning/azathoth/summary.md` (this file)
- `azathoth/` — pyproject.toml, uv.lock, Makefile, README, and
  `src/azathoth/{settings,openai_models,acp_client,app}.py` with
  42 hermetic unit tests (fake ACP agent over stdio) and one opt-in
  integration test for a real `vibe-acp`.

## Verification

From `azathoth/`: `make install`, `make check` (ruff, mypy, deptry, lock
check) and `make test` (hermetic unit tests) are green; `uvx reuse lint` is
green from the repository root. A live demo (server + fake agent + HTTP
requests) verified `/health`, the `chat.completion` body, the SSE stream and
the OpenAI-shaped 404.

## Possible future refinements

- Token `usage` accounting from the agent's `usage_update` notifications
  (currently reported as zeros).
- Server-side session reuse or ACP session-loading for long conversations,
  trading statelessness for token cost.
- Model-option discovery endpoint (`/v1/models`) if clients need it.
