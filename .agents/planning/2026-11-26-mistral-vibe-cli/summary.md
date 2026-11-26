# Summary: the mistral-vibe-cli agent skill

## Artifacts created

- `skills/mistral-vibe-cli/SKILL.md` — the new distributable skill: a port of
  the Hermes Agent `opencode` delegation skill to the Mistral Vibe CLI, in
  the epinoia SOP format and passing both the agent-sop-author validation
  (0 errors, 0 warnings) and the `skills-ref` Agent Skills specification
  check.
- `Makefile` — the install target now installs an explicit, guarded
  `SKILLS` list (including `mistral-vibe-cli`) into
  `TARGET_DIR/.agents/skills/`, failing loudly when a listed skill is
  missing.
- `tests/test-install.sh` — per-skill install assertions plus a
  skill-registry-guard group (44 tests total, all passing).
- `.github/workflows/tests.yml` — CI running `make test` and the aletheia
  pytest suite on every pull request and every merge to main.
- `REUSE.toml` — compliance annotations for the new original content.
- PDD records under `.agents/planning/2026-11-26-mistral-vibe-cli/`:
  `rough-idea.md`, `idea-honing.md`, `research/vibe-cli-capabilities.md`,
  `research/hermes-opencode-port.md`, `design/detailed-design.md` (+ rev1
  review), `implementation/plan.md`, the per-step review files
  (`step-1-review-rev{1,2}.md`, `step-2-review-rev1.md`,
  `step-3-4-review-rev1.md`), and this summary.

## Overview of the design and implementation

The skill teaches an agent to delegate coding tasks to the Vibe CLI's
programmatic mode: readiness checks, a self-contained task brief, bounded
runs (`--max-turns`/`--time-limit`/`--max-tokens`), the approval semantics
of unattended runs (denials vs. `--auto-approve` vs. config-based
permissions), exit-code triage, session continuation (`--continue` /
`--resume`), parallel isolation with `--worktree`, and independent
verification of the worker's output. The Makefile, tests, workflow, and
compliance metadata make the skill a first-class installed and CI-checked
citizen of the repository.

## Review history

- Design: 1 review round; all findings incorporated.
- Step 1 (skill): 2 rounds; rev2 verdict Ship.
- Step 2 (Makefile + install tests): 1 round; verdict Ship.
- Steps 3+4 (compliance + CI workflow): 1 round; verdict Ship.

## Verification results

- `validate-skill.sh skills/mistral-vibe-cli`: 0 errors, 0 warnings
  (includes `skills-ref` spec validation).
- `make test`: all 3 hermetic suites pass (requires the `opencode` binary —
  installed by CI; without it the dry-run suites fail by design).
- `uvx reuse lint`: clean.
- `make -C aletheia install test`: 97 tests pass.

## Next steps

- Merge the PR; the new CI workflow will run on the merge and all future
  PRs.
- Optionally extend the CI workflow with `make -C aletheia check`
  (mypy/ruff) and the web UI build if desired.
- Revisit the skill when the Vibe CLI grows a non-interactive PR review or
  cost-reporting command, to keep the pitfalls section truthful.
