# Research: Mistral Vibe CLI capabilities relevant to delegation

Sources: official docs index https://docs.mistral.ai/llms/vibe/code/llms.txt,
CLI page https://docs.mistral.ai/llms/vibe/code/cli/llms.txt, and
"Work with the CLI" https://docs.mistral.ai/llms/vibe/code/cli/work-with-cli
(all fetched 2026-11-26). Source code: https://github.com/mistralai/mistral-vibe.

## Installation and readiness

- One-line installer (macOS/Linux): `curl -LsSf https://mistral.ai/vibe/install.sh | bash`;
  manual: `uv tool install --python 3.14 mistral-vibe`; Windows via `uv tool install`.
- The binary is `vibe` (plus `vibe-acp` for ACP clients).
- Readiness checks: `vibe --version` returns a version; `vibe --version` plus a
  small programmatic prompt verifies API access.
- Auth: setup wizard on first launch (`vibe --setup` reruns it), or
  `MISTRAL_API_KEY` in the environment; credentials live in the OS keyring or
  `~/.vibe/.env`.
- Update with `vibe update` (or `vibe --check-upgrade`).

## Modes

- Interactive (default TUI): `vibe` or `vibe "prompt"`.
- **Programmatic mode** — the delegation workhorse: `vibe --prompt "..."` (alias
  `-p`), reads the prompt from `--prompt-file PATH` or from stdin when `-p`
  has no text. No TUI, no interactive tools; runs with `default_agent`
  (`accept-edits` unless configured).

## Programmatic mode options (facts the skill must state correctly)

- `--auto-approve` (alias `--yolo`) approves every tool call; without it, any
  tool call needing approval is **denied** (nobody can answer a prompt). An
  admin can block `--auto-approve` via `enable_auto_approve = false`; then
  `permission = "always"` or bash allowlists in config are the fallback.
- `--agent NAME` picks the built-in agent: ask, accept-edits (default),
  smart-approve, auto-approve.
- `--model ALIAS`, `--thinking LEVEL` (e.g. low/high) apply to a new session
  without saving it.
- `--max-turns N` caps assistant turns (recommended to bound runs);
  `--max-tokens N` caps total tokens including subagents; `--max-price DOLLARS`
  caps cost (indicative only, depends on config prices); `--time-limit SECONDS`
  stops after a deadline (resumable), SIGTERM behaves the same.
- `--enabled-tools TOOL` (exact names, globs like `bash*`, regex `re:...`,
  repeatable), `--disabled-tools TOOL` (repeatable).
- `--output text|json|streaming`: text prints the final answer; json prints
  session messages as a JSON array at the end; streaming prints one JSON
  object per message.
- `--output-dir DIR` writes `export.json` (version, effective config, token
  usage, cost, stop reason, outcome, subagent breakdown) plus a session copy,
  however the run ends. Denied tool calls are reported on stderr and in the
  export's `warnings`.
- `--system-prompt-file PATH` replaces Vibe's own system-prompt text
  (project context and AGENTS.md still follow).
- Exit codes: 0 finished; 1 could not start (invalid flag/config); 2 model API
  or runtime failure; 3 stopped before finishing (limit reached, stopped, or
  model declined). If the agent finishes without an answer, Vibe says so on
  stderr.

## Sessions and continuation

- `vibe --continue` / `-c` resumes the most recent session (terminal-scoped,
  falls back to the directory's latest); `vibe --resume` opens a picker;
  `vibe --resume SESSION_ID` resumes an exact session (works from anywhere;
  accepts the 8-character short ID).
- Programmatic mode supports continuation: `-p` combined with `-c` or
  `--resume SESSION_ID`.
- Session logging (`[session_logging] enabled = true` in `~/.vibe/config.toml`,
  on by default) is required for resume.
- A resumed session keeps its last agent and model, even if `--agent` is passed.

## Trust

- Both modes enforce folder trust; only interactive mode can show the prompt, so
  programmatic runs in a not-yet-trusted folder need `vibe --trust` (trust for
  that invocation only). Trusted folders are stored in
  `~/.vibe/trusted_folders.toml`.

## Parallel isolation

- `--worktree [NAME]` runs the session in its own git worktree under
  `~/.vibe/worktrees/` (branch named after it; reused if it exists; a prompt
  must come first because `--worktree` reads the next argument as the name).
  `--worktree` also grants trust for that run. Programmatic runs leave the
  worktree in place.

## Goals and interactive controls (context for pitfalls, not delegation)

- Interactive `/goal`, `/model`, `/resume`, `/branch`, `/rewind`, `!shell`,
  `@file` references, queued messages, and agent cycling with Shift+Tab.
- Goals are not available in programmatic mode.

## Capability gaps vs OpenCode (dropped from the port)

- No `pr <number>` subcommand: PR review must be a normal delegated prompt.
- No `stats`/`session list` CLIs: cost data comes from `--output-dir`
  `export.json` per run instead.
- No `--format json` event stream flag; the equivalent is `--output json|streaming`.

## Also noted

- Commands run by Vibe get `VIBE_SESSION=1` in their environment.
- `vibe config schema` prints the local config schema if checks are needed.
