# Review Notes

<!-- tags: review, gaps, recommendations -->

## Consistency check

No contradictions were found between `README.md`, `DEVELOPER_GUIDE.md`, the `Makefile`, the skills, and the tests.

Points verified:

- The two skill trees are described consistently: `skills/` holds distributable artifacts and `.agents/skills/` holds development-only skills.
- `make install` placement matches the discovery rules documented for Zed, opencode, and Mistral Vibe, and matches the assertions in `tests/test-install.sh`.
- The review subject table in `skills/ponytail-review-pdd/SKILL.md` matches the review-file naming implemented by `run-review.sh`.
- The model default is not duplicated: the opencode agent frontmatter is the single source of truth, and `test-run-review.sh` proves the script follows it.
- The licensing table in this knowledge base matches `THIRD-PARTY-NOTICES.md`, `REUSE.toml`, and the `LICENSE` sidecars.

Minor documentation nuances found:

1. `DEVELOPER_GUIDE.md` says the Vibe agent restricts itself with `enabled_tools`/`disabled_tools`, but `.vibe/agents/ponytail-reviewer.toml` defines only `enabled_tools` plus `[tools.bash]` and `[tools.write_file]` allow/deny lists. The restriction is real; the guide names one mechanism too many.
2. `skills/ponytail-review-pdd/SKILL.md` describes the default model as `mistral/zai-glm-5-3`, while the agent's line is `mistral/zai-glm-5-3#max`. The model matches; the variant is intentionally taken from the same line. The wording could mention the variant.

## Completeness check

Areas with limited coverage:

- **Vibe configuration is untested.** `tests/test-install.sh` asserts that `.vibe/config.toml` and the Vibe agent are copied, but no test validates the TOML, the model alias, the context limits, or the agent's tool permissions. `vibe config schema` is the available schema check but is not wired into the suite.
- **No schema validation for opencode config.** Permission entries are exercised indirectly by the live e2e permissions test, but `opencode.json` itself is not validated offline.
- **Upstream drift is unchecked.** `skills/pdd`, `skills/codebase-summary`, and `.agents/skills/agent-sop-author` are modified derivatives of `strands-agents/agent-sop`; nothing compares them with a newer upstream. The same applies to the verbatim ponytail skill.
- **Full reviews are deliberately not automated.** The hermetic suite covers orchestration with a stubbed `opencode`; the live suite only proves the agent runs and permissions hold. No automated test judges review quality.
- **No shell linting.** Scripts are tested behaviorally but not checked with `shellcheck` or `shfmt`.
- **macOS portability is untested.** `test-run-review.sh` uses GNU `sed -i`; the UUID fallback and relative-path fallback are exercised only on Linux.
- **No CI configuration in this directory.** Any workflows live at the repository's git root, outside this package, so their coverage could not be verified here.
- **Test fixtures accumulate.** Suites intentionally leave their workspaces under `.local/` for inspection; repeated runs grow that directory until it is cleaned.
- **`validate-skill.sh` has no test of its own.** It is used manually and runs an external `uvx` validator that needs network access or a warm cache.

## Recommendations

1. Add a small Vibe config test (for example, `vibe config schema` plus assertions on the `reviewer` alias and `active_model`) if Vibe is part of the supported developer workflow.
2. Add `shellcheck` to the test workflow; the scripts rely on subtle `set -euo pipefail` behavior and quoting.
3. Record upstream commit hashes next to derived skills (in the `LICENSE` sidecars or `THIRD-PARTY-NOTICES.md`) to make drift checks possible.
4. If macOS support is expected, replace `sed -i` with a portable helper and run the suite there.
5. Keep `AGENTS.md` and this knowledge base in sync after changes to skill layout, install placement, review file naming, or the model default.
6. Document the Vibe review path in the same level of detail as the opencode path, or explicitly mark it as a manual alternative (it is currently tested only by installation).

## Note on generated content

This knowledge base was generated from the code and documentation at the time of the run. It intentionally avoids volatile metrics (line counts, file sizes, test counts). Update the affected files when those structural facts change.
