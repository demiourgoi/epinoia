# Implementation Plan: mistral-vibe-cli agent skill

## Checklist

- [x] Step 1: Create the `mistral-vibe-cli` skill and validate it
- [ ] Step 2: Make the Makefile install target install the skill explicitly
- [ ] Step 3: Final verification and compliance

## Working agreements

Proceed step by step:

- After each step, ask me for confirmation before completing it
- When completing a step, add an "Implementation notes" subsection to its section in the plan, summarizing what we did, focusing on deviations from the plan, why we made them, and implications for subsequent steps

This task runs fully unattended, so no confirmation is requested between
steps; the implementing agent decides and records deviations here.

Additional working agreements:

- Run `.agents/skills/agent-sop-author/validate-skill.sh skills/mistral-vibe-cli`
  after every skill change and fix all errors.
- Run `make test` and `uvx reuse lint` before declaring a step done.
- One commit per implementation step; a ponytail review after each step,
  with the review file stored next to this plan, at most three rounds per
  review target.

## Step 1: Create the `mistral-vibe-cli` skill and validate it

**Objective:** Deliver `skills/mistral-vibe-cli/SKILL.md` implementing R1–R3
and R7: spec-compliant frontmatter (`name: mistral-vibe-cli`,
`description`, `license: MIT`, `compatibility`, `metadata`) and the epinoia
SOP body (Overview, Parameters with acquisition constraints, seven numbered
Steps with Constraints, Pitfalls, Examples, Troubleshooting) covering
readiness, bounded one-shot delegation, approval semantics, exit codes,
session continuation, trust, parallel worktrees, and verification, all in
English.

**Guidance:** Write fresh against the official Vibe CLI documentation;
port the Hermes opencode capability set, not its prose. Keep `SKILL.md`
under 500 lines. No scripts directory (design, Appendix A).

**Tests:** `validate-skill.sh skills/mistral-vibe-cli` exits 0 (includes
the `skills-ref` spec validation); the SKILL.md line count stays under 500.

**Integration:** Standalone new directory; nothing else changes yet. The
unmodified `make install` (wildcard copy) already picks it up, so the skill
is demoable end-to-end right after this step.

**Demo:** `make install TARGET_DIR=<tmp>` shows
`<tmp>/.agents/skills/mistral-vibe-cli/SKILL.md`, and the validator passes.

## Step 2: Make the Makefile install target install the skill explicitly

**Objective:** Implement R4: add the `SKILLS` variable listing all six
distributable skills (including `mistral-vibe-cli`), make the install recipe
check each listed skill exists (exit 2 with a clear message naming a missing
skill), copy each listed skill into `TARGET_DIR/.agents/skills/`, and echo
the installed list; extend `tests/test-install.sh` with per-skill assertions
(Require 5) and a "skill registry guard" group that removes a listed skill
from a temp copy of the repo and asserts the guarded failure.

**Guidance:** Preserve the placement rules and guards: skills to
`TARGET_DIR/.agents/skills/`, opencode files to the target's git root,
`.vibe/` to `TARGET_DIR`, and the existing self-install/missing-target
error messages and exit codes. Guard-test with a copy of the repo without
`.git` (design, R5). Keep the tests hermetic.

**Tests:** New assertions in `tests/test-install.sh`; `make test` passes
overall.

**Integration:** Builds on the Step 1 skill: the registry guard and the
per-skill assertions reference `mistral-vibe-cli`.

**Demo:** `make install TARGET_DIR=<tmp>` prints the installed skill list
including `mistral-vibe-cli`; `make test` is green; a repo copy with a listed
skill removed fails the install with the missing-skill message.

## Step 3: Final verification and compliance

**Objective:** Implement R2 and R6 end to end: add
`skills/mistral-vibe-cli/SKILL.md` to the original-content block in
`REUSE.toml`, confirm `THIRD-PARTY-NOTICES.md` needs no entry (no third-party
text embedded), and run the full gate: `validate-skill.sh`, `make test`,
`uvx reuse lint`.

**Guidance:** No scope creep — this step only wires compliance metadata and
runs the gates; functional gaps found here go back to Steps 1–2.

**Tests:** `make test` (all hermetic suites) and `uvx reuse lint` both pass.

**Integration:** Completes R1–R8; the change is ready for the PR.

**Demo:** All gates green in one pass; `git status` clean apart from the
PDD artifacts.

## Step 1: Implementation notes

Implemented `skills/mistral-vibe-cli/SKILL.md` (296 lines) with the
spec-compliant frontmatter (`name`, `description`, `license: MIT`,
`compatibility`, `metadata` with author/version) and the SOP body. The seven
steps, pitfalls, examples, and troubleshooting sections follow the design
without deviation. Two reviewer-caught fixes during self-review before
committing: the parallel-worktree example first showed an invalid
invocation (`--prompt` without a value after a positional prompt), corrected
to `vibe "prompt" --worktree NAME`; and negative constraints were reworded so
the validator's same-line-context heuristic stops warning (all MUST NOT
bullets now carry "because" on the constraint line). Validation:
`validate-skill.sh skills/mistral-vibe-cli` exits 0 with zero warnings,
including the `skills-ref` Agent Skills specification check. Demo: a temp
`make install` places `.agents/skills/mistral-vibe-cli/SKILL.md` (still via
the wildcard copy until Step 2).

### Step 1: review outcome

Review rev1 found one must-fix: the parallel-worktree examples used a
positional prompt, which starts the interactive TUI the skill itself forbids;
they now use `vibe --prompt ... --worktree NAME`. Also fixed: the Overview no
longer implies every run prints a JSON transcript; the `@path` example is
now a concrete invocation; the `VIBE_SESSION=1` constraint is stated plainly.
Rev2 confirms: Ship. Validation still passes with zero warnings after the
fixes.
