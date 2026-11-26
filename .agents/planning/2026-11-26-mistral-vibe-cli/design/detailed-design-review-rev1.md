# Design Review — rev1

Reviewer: ponytail-review, applied to `detailed-design.md` (commit f62bc06).

**What this change does:** Designs a new epinoia skill
`skills/mistral-vibe-cli/` that teaches agents to delegate coding tasks to
the Mistral Vibe CLI, plus an explicit, guarded skill list in the Makefile
install target, test updates, and REUSE annotation.

## Must fix

1. **The validation command in the design is misspelled** (design, R2)
   - **What this is:** R2 quotes the authoritative validator command.
   - **Problem:** It reads `uvx --from skills-ref agentsskills validate`
     (doubled "s"). An agent following the design would run a command that
     does not exist and mistake the failure for a skill problem.
   - **Fix:** Use the exact command from the repo's own validator script:
     `uvx --from skills-ref agentskills validate`.

2. **The REUSE component says both true and false things about which files
   are new** (design, Component 4)
   - **What this is:** Component 4 describes the `REUSE.toml` change.
   - **Problem:** It calls `Makefile` and `tests/test-install.sh` "newly
     listed paths" and then says they are "already annotated". Only
     `skills/mistral-vibe-cli/SKILL.md` is a new file; the other two already
     appear in the original-content block and need no REUSE change.
   - **Fix:** State it plainly: only the SKILL.md path is added to the
     existing original-content annotation; the Makefile and test files are
     already covered.

## Should fix

3. **R5 does not say how the registry guard avoids a self-install exit**
   (design, R5 / Component 3)
   - **What this is:** The new test removes a skill but keeps it listed in
     the Makefile, then expects the install to fail with the missing-skill
     error.
   - **Problem:** The install target refuses to run when `TARGET_DIR`
     resolves to the repository itself, so the guard test must run against a
     copy of this repo, not the repo itself. Component 3 mentions the copy,
     but the requirement (R5) reads as if it applies to the real repo.
   - **Fix:** Mention the repo copy in R5 as well, so requirement and design
     match.

## Nice to have

4. **Appendix A wording**: "a wizard or a portfolio-based shell wrapper" —
   "portfolio-based" is not a meaningful description here. Reword to
   "wrapper scripts around common `vibe` invocations".

**Verdict: fix 1 and 2 first.** (3 and 4 applied in the same pass.)
