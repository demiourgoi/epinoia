---
name: mistral-vibe-cli
description: >
  Delegate coding tasks to the Mistral Vibe CLI (vibe). Runs bounded
  non-interactive coding sessions with `vibe --prompt`, resumes saved
  sessions for iterative work, runs parallel tasks in isolated git
  worktrees, and verifies the results. Use when you want an external
  coding agent to implement, refactor, debug, review, or test code with the
  Vibe CLI, or when the user explicitly asks to use vibe.
license: MIT
compatibility: Requires the Mistral Vibe CLI (`vibe`) on PATH with credentials configured, and git for repository tasks.
metadata:
  author: demiourgoi
  version: "1.0.0"
---

# Mistral Vibe CLI

## Overview

This skill lets you delegate coding work to the
[Vibe Code CLI](https://docs.mistral.ai/llms/vibe/code/cli) — the `vibe`
binary from [mistralai/mistral-vibe](https://github.com/mistralai/mistral-vibe)
— as an autonomous coding worker. It is a port of the Hermes Agent `opencode`
delegation skill, translated to Vibe: instead of managing an interactive TUI
in the background, you run Vibe's **programmatic mode** (`vibe --prompt`),
which executes a task as a bounded non-interactive process and exits with
the final answer (or a full JSON transcript with `--output json`) and a
documented exit code.

Vibe runs in your working directory with read/write access, a shell, and
configurable tools, so treat every delegated task like any other subprocess
that changes files: scope it, bound it, and verify the result yourself.

## Parameters

- **coding_task** (required): What the delegated agent must do. A
  self-contained task description: goal, affected files or modules,
  constraints, and the acceptance criteria (tests to run, expected result).
- **workdir** (optional, default: current repository root): The directory the
  delegated `vibe` process runs in. Keep one repository (or git worktree) per
  session to avoid collisions.
- **mode** (optional, default: `one-shot`): `one-shot` for a bounded single
  run, or `continue` for iterating on a previously saved session with
  `--continue` / `--resume`.
- **bounds** (optional): Limits for the run, from `--max-turns`,
  `--max-tokens`, `--max-price`, and `--time-limit`. Prefer at least
  `--max-turns` so a runaway task stops on its own.
- **options** (optional): Session knobs: `--agent` (ask, accept-edits,
  smart-approve, auto-approve), `--model ALIAS`, `--thinking LEVEL`,
  `--output text|json|streaming`, `--output-dir DIR`, `--worktree NAME`,
  `--trust`.

**Constraints for parameter acquisition:**

- You MUST ask the user for all required parameters in a single prompt, not
  one at a time.
- You MUST accept the coding task as direct text, a file path, or a URL to a
  task description (fetch it yourself if the environment allows).
- You SHOULD propose defaults for optional parameters instead of blocking:
  `one-shot` mode, the repository root as workdir, and a modest turn cap.
- You MUST NOT invent a model alias, because an unknown alias fails the run
  with exit code 1; only pass `--model` with an alias the user names or one
  you verified exists in the Vibe config.

## Steps

### 1. Verify readiness

Before delegating, confirm the CLI and its credentials work.

**Constraints:**

- You MUST verify the binary before planning around it:
  `vibe --version` (non-zero or missing binary means install or PATH fixing
  comes first).
- You SHOULD confirm credentials with a tiny smoke run instead of assuming
  them: `vibe --prompt 'Reply with exactly: VIBE_SMOKE_OK' --max-turns 1`.
- You MUST NOT start an interactive `vibe` session for delegation, because
  the interactive TUI cannot be driven from a non-interactive agent; use
  programmatic mode only.

### 2. Compose the delegation prompt

Write the task as a complete brief for an agent that shares the working
directory but not this conversation.

**Constraints:**

- You MUST make the prompt self-contained: goal, language and framework
  conventions, files or modules to touch, what NOT to change, and the
  acceptance criteria.
- You MUST include the commands that prove success (for example the test
  command) and instruct the worker to run them.
- You SHOULD give the worker explicit paths instead of vague references,
  because it cannot ask you follow-up questions mid-run in programmatic mode.
- You MUST use `--prompt-file PATH`, or `-p` with the prompt piped on stdin,
  when the task text is long or contains characters your shell mangles,
  because quoting bugs silently corrupt the task.

### 3. Run a bounded one-shot task

Execute the delegated task in programmatic mode.

**Constraints:**

- You MUST always bound the run with `--max-turns`, and SHOULD add
  `--time-limit` (resumable) or `--max-tokens` for untrusted or costly tasks,
  so a stuck task stops by itself instead of burning tokens.
- You MUST run with an explicit approval posture and know its cost:
  - default (e.g. `accept-edits`) may leave tool calls **denied** — nobody can
    answer an approval prompt inside a programmatic run, and denials are
    reported on stderr and in the export's warnings;
  - `--agent auto-approve` or `--auto-approve` (alias `--yolo`) approves every
    tool call — use only in a disposable worktree or a throwaway clone, since
    it also approves shell commands;
  - if an administrator blocked `--auto-approve` (`enable_auto_approve =
    false`), plan for per-tool `permission = "always"` config or bash
    allowlists instead, and expect denials otherwise.
- You MUST handle folder trust in programmatic mode: the confirmation prompt
  only appears in interactive mode, so a not-yet-trusted directory needs
  `--trust` for that invocation (or `--worktree`, which trusts its run).
- You SHOULD pass `--output json` and `--output-dir DIR` when you need the
  full transcript plus `export.json` (token usage, cost, stop reason,
  warnings, subagent breakdown) for auditing.
- You SHOULD know that commands Vibe runs get `VIBE_SESSION=1` in their
  environment, so logs and hook scripts can detect that they ran under Vibe.

### 4. Interpret the outcome

Read the exit code and the output before touching the result.

**Constraints:**

- You MUST interpret the exit codes correctly:

  | Exit code | Meaning | Your reaction |
  | --- | --- | --- |
  | `0` | The agent finished | verify the result (step 7) |
  | `1` | Could not start: invalid flag or config | fix the invocation, re-run small |
  | `2` | Model API or runtime failure | check credentials/billing and re-run |
  | `3` | Stopped before finishing: a limit was reached, the run was stopped, or the model declined | inspect, then continue the session with `--continue`/`--resume` |

- You MUST read stderr as well as stdout: Vibe reports each denied tool call
  and runs that finish without an answer there.
- You MUST NOT re-run blindly on failure, because the same invocation fails
  the same way twice and spends tokens to do it; fix the named cause (bad
  flag, missing credential, denied tool) first.

### 5. Iterate on a session

When one pass is not enough, continue the same session instead of starting
over.

**Constraints:**

- You MUST use `vibe --prompt '<follow-up>' --continue` (latest session of
  this terminal/directory) or `vibe --prompt '<follow-up>' --resume
  SESSION_ID` (exact or 8-character short ID) to continue, because the session
  keeps the original task context.
- You MUST keep session logging enabled (`[session_logging] enabled = true`
  in `~/.vibe/config.toml`, the default) when you rely on continuation,
  because resume stops working without it.
- You MUST NOT rely on `--agent` or `--model` at resume time, because the
  resumed session keeps the agent and model it last ran on.

### 6. Run isolated parallel tasks

For independent tasks, isolate each worker in its own git worktree.

**Constraints:**

- You SHOULD use `--worktree` for parallel or risky tasks: Vibe creates (or
  reuses) a worktree under `~/.vibe/worktrees/` on a matching branch and
  trusts it for that run.
- You MUST put the prompt first when the worktree takes a name, because
  `--worktree` reads the *next* argument as the worktree name.
- You MUST NOT share a working directory between delegated sessions, because
  two agents editing the same checkout overwrite each other's changes.
- You SHOULD copy finished work out of a programmatic-mode worktree yourself
  (cherry-pick, branch merge), because programmatic runs leave the worktree
  in place.

### 7. Verify and report

Treat the worker's claims as unverified until you check them.

**Constraints:**

- You MUST inspect the actual diff (`git status`, `git diff`) and run the
  project's test or build commands yourself; a delegated agent can believe it
  succeeded when it did not.
- You MUST report concrete results: files changed, commands run, pass/fail
  status, and remaining risks — not a summary of the agent's own summary.
- You SHOULD keep the `export.json` from `--output-dir` when the user needs
  token usage and cost accounting for the delegation.

## Pitfalls

- **Silent denials:** in programmatic mode every tool call that needs approval
  is denied, and denial messages go to stderr (and `export.json` `warnings`).
  A run that "does nothing" is usually a denied run.
- **`--auto-approve` can be blocked** centrally (`enable_auto_approve =
  false`); do not build a workflow that assumes it always works.
- **Long prompts:** pass them with `--prompt-file` or stdin; shell quoting
  bugs truncate or mangle tasks.
- **No `pr`, `stats`, or `session list` subcommands exist** in the Vibe CLI:
  review a PR with a normal delegated prompt describing the review, get costs
  from each run's `export.json`, and get session IDs from the output of the
  run that started them (or resume with `--continue`).
- **Interactive-only features** (`/goal`, queued messages, question prompts)
  are unavailable in programmatic mode; plan bounded runs instead.
- **Exit code 3 is not a failure of your task**, only of that run: the
  session is resumable, so continue it with a bigger budget rather than
  losing the context.

## Examples

### One-shot bounded task

```bash
vibe --prompt "Add retry logic to the API client in src/api.py, following the
existing style. Run pytest tests/test_api.py and make it pass. Do not touch
unrelated files." --max-turns 25 --output json
```

### Long or quote-heavy prompt from a file

```bash
vibe --prompt-file task-brief.md --max-turns 30 --output-dir .local/vibe-run
```

### Readiness smoke test

```bash
vibe --version
vibe --prompt 'Reply with exactly: VIBE_SMOKE_OK' --max-turns 1
```

### Continue the previous session with a follow-up

```bash
vibe --prompt "Now handle token expiry errors in the same retry logic, and
re-run the API tests." --continue
```

### Parallel isolated tasks

```bash
vibe --prompt "Fix issue #101 and commit" --worktree issue-101
vibe --prompt "Add regression tests for the parser and commit" --worktree parser-tests
```

### Reference files in a prompt

```bash
vibe --prompt "Read @src/agent.py and add error handling for network
failures, then run the test suite." --max-turns 20
```

## Troubleshooting

### `command not found: vibe`

Install per the
[CLI docs](https://docs.mistral.ai/llms/vibe/code/cli):
`curl -LsSf https://mistral.ai/vibe/install.sh | bash`, or
`uv tool install --python 3.14 mistral-vibe`. Re-run `vibe --version` after
fixing PATH.

### Exit code 1 on every run

An invalid flag or a broken config. Check the invocation against `vibe
--help` and the [programmatic mode
options](https://docs.mistral.ai/llms/vibe/code/cli/work-with-cli); try a
minimal smoke run.

### Exit code 2

Model API or runtime failure: missing key (`MISTRAL_API_KEY`, OS keyring, or
`~/.vibe/.env`), bad key, quota, or provider outage. Rerun `vibe --setup` or
set `MISTRAL_API_KEY`.

### Nothing happened, exit 0

Read stderr: tool calls were probably denied for approval. Switch to
`--agent auto-approve` (or `--auto-approve`) in a disposable worktree, or
widen permissions in `config.toml`.

### Untrusted-folder error, or config ignored

Programmatic runs enforce trust with no prompt. Pass `--trust` for this
invocation, or use `--worktree`, which trusts its run.

### `--continue` cannot find the session

The directory has no session, or session logging was disabled. Set
`[session_logging] enabled = true` in `~/.vibe/config.toml` and prefer
explicit `--resume SESSION_ID` with the ID printed by the original run.
