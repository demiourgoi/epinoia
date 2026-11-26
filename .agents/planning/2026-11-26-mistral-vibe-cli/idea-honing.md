# Idea Honing

This task runs fully unattended, so the questions below were resolved by the
implementing agent using the repository conventions (AGENTS.md), the referenced
documentation, and the unattended-coding working agreements, instead of
interactively with the user.

## Q1: What exactly is ported from the Hermes `opencode` skill?

**Decision:** The functional scope, not the text. The Hermes skill teaches an
agent to delegate coding to the OpenCode CLI: readiness checks, one-shot
non-interactive runs, interactive background sessions with progress polling,
session resume, model/agent selection, isolated parallel work, PR review, and a
smoke test. The port keeps this functional core (readiness checks,
programmatic delegation, session continuation, parallel isolation, smoke
verification) but adapts every command, flag, mode, and pitfall to the Mistral
Vibe CLI, where the equivalents differ substantially:

- Vibe's non-interactive mode is programmatic mode (`vibe --prompt`/`-p`,
  `--max-turns`, `--output json`, `--auto-approve`, `--time-limit`), not
  `opencode run`.
- Vibe has no `pr` subcommand or `stats`/`session list` commands, so those
  Hermes sections are dropped rather than invented.
- Vibe's trust model (`--trust`, trusted folders) and approval deny behavior
  in programmatic mode are Vibe-specific pitfalls worth covering.
- Vibe offers `--worktree` for parallel isolation, which replaces the Hermes
  manual scratch-workdir pattern.

## Q2: Which document structure does the skill follow: the Hermes layout or the epinoia SOP layout?

**Decision:** The epinoia SOP layout, validated by
`.agents/skills/agent-sop-author/validate-skill.sh`. AGENTS.md convention 8
says skill authoring is validated, not improvised, and requires Overview,
Parameters, and numbered Steps with Constraints. The Hermes layout (When to
Use, Common Flags, Pitfalls) maps cleanly onto that structure: the Hermes
content becomes the step constraints and the pitfalls/troubleshooting sections.
The skill must pass the `skills-ref` Agent Skills specification validation as
well, so the frontmatter follows the spec fields (`name` matching the
directory, `description` under 1024 characters, `license`,
`compatibility`, `metadata`).

## Q3: How are approvals handled when delegating to Vibe non-interactively?

**Decision:** The skill teaches the documented behavior: in programmatic mode
nobody can answer an approval prompt, so Vibe denies any tool call that needs
one; the delegating agent must either pass `--auto-approve` for trusted runs
or plan for denied calls and use a permissive agent (`auto-approve`) or bash
allowlists in `config.toml`. The skill states when each is appropriate and
records the exit codes (0/1/2/3) so callers can interpret outcomes.

## Q4: What does "update the install target in the Makefile" mean, given that `make install` already copies the whole `skills/` tree?

**Decision:** Make the installed skills explicit in the Makefile. Today
`install` copies `skills/.` wholesale, so the new skill would install as a
side effect. To make the install target name the new skill instead of relying
on an implicit wildcard, introduce an explicit, guarded list: the Makefile
defines the skills it installs, fails with a clear error if a listed skill
directory is missing, and echoes the installed list. Tests assert that every
listed skill lands in `TARGET_DIR/.agents/skills/`, including
`mistral-vibe-cli`, and exercise the new guard. This keeps installs
declarative, makes a future missing-skill mistake fail loudly, and satisfies
the requirement verbatim.

## Q5: What parameters does the skill expose?

**Decision:** A small set matching how a delegating agent works: the coding
task prompt (required), the working directory (required, defaults to the
current repo root), the execution mode (one-shot bounded run vs. iterative
resumed session), and optional model/thinking/budget knobs that Vibe supports
(`--model`, `--thinking`, `--max-turns`, `--max-tokens`, `--max-price`,
`--time-limit`, `--agent`, `--worktree`). The skill must instruct acquiring
all parameters up front in a single prompt.

## Q6: Licensing and compliance for the new files?

**Decision:** The skill is written fresh against the official Mistral Vibe
CLI documentation, in the epinoia SOP format; it is not a derivative copy of
the Hermes text (the Hermes skill itself declares MIT). The new
`skills/mistral-vibe-cli/SKILL.md` is original demiourgoi content under MIT,
needs a `REUSE.toml` annotation (original content block), and no
`THIRD-PARTY-NOTICES.md` entry because no upstream text is embedded. The
Makefile and test changes join the existing original-content annotation.

## Q7: Where do the PDD artifacts live and what language are they in?

**Decision:** In this repository at
`.agents/planning/2026-11-26-mistral-vibe-cli/` (the date prefix and kebab-case
name follow the pdd skill conventions; the aletheia project shows the same
pattern nested under its own root). All PDD artifacts and code comments are
in English.
