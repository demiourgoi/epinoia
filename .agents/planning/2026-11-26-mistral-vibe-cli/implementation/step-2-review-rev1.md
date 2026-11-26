# Step 2 Review — rev1

Reviewer: ponytail-review, applied to the Makefile `install` target and
`tests/test-install.sh` (uncommitted working tree of commit 55c4951).
Load assumption: a single developer or CI runner installing skills into a
project.

**What this change does:** The install target now names the skills it
installs in a `SKILLS` variable (including the new `mistral-vibe-cli`),
fails with a clear error when a listed skill directory is missing, copies
each listed skill individually, and echoes the list. The install tests gain
per-skill assertions and a registry-guard group.

## Checks done

- Guard runs after the existing TARGET_DIR guards, so self-install and
  missing-target keep their messages and exit code 2; the new guard also
  exits 2 and names the missing skill.
- Nothing is copied when the guard fires (asserted via `.vibe/config.toml`
  missing in the guard target).
- The success echo changed from a path to the skill list plus a destination
  line; no test asserted the old wording, so no breakage.
- The guard test copies the repository without `.git` and `.local` before
  removing a skill; the copy is required because the recipe refuses to read
  a repository it is installing into (its `REPO_DIR` is the copy's own
  Makefile). All 44 install tests pass.
- Behavior change (deliberate, commented in the Makefile): an unlisted
  directory under `skills/` is no longer installed. The per-skill test loop
  intentionally repeats the list: it pins the contract between `SKILLS` and
  the tree, which is exactly what the guard protects.

## Findings

- **Nice to have:** The `Skill registry guard` test could parse `SKILLS`
  from the copied Makefile instead of hardcoding the list, so a rename or
  addition updates one place. Not worth it: the hardcoded list is also the
  contract check that new skills are added here deliberately, and it is six
  entries next to the variable it mirrors.
- No must-fix or should-fix findings. The guard loop and copy loop are two
  lines each; no simpler formulation copies an explicit list.

Looks good. **Verdict: Ship.**

**Not checked:** `make -C . install` edge beyond the suite's guard tests
(none needed); the workflow file is out of scope for this step.
