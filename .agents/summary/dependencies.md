# Dependencies

<!-- tags: dependencies, external-tools, licenses -->

## Runtime tools

| Dependency | Required by | Notes |
| --- | --- | --- |
| `bash` | All scripts, Makefile recipes | Scripts use `set -euo pipefail`, arrays, process substitution, and `[[ ]]` |
| `git` | `make install`, `compute-diff.sh`, `run-review.sh`, tests | The installer resolves the target's git root; the reviewer runs at it |
| `make` | `make install`, `make test`, `make test-e2e` | Thin wrappers over the shell entry points |
| `opencode` | `run-review.sh`, e2e suites | Must be authenticated for the selected model's provider |
| `uvx` | `validate-skill.sh`, `update-third-party-notices`, `bin/agent-sop-to-skill.sh` | Downloads `reuse`, `skills-ref`, and `strands-agents-sops` on first use |
| Standard Unix tools | Scripts and tests | `sed`, `grep`, `find`, `mktemp`, `dirname`, `basename`, `realpath`/`readlink`, `tail`, `date` |

### Optional helpers

| Helper | Fallback |
| --- | --- |
| `uuidgen` | `/proc/sys/kernel/random/uuid`, then `python3 -c 'import uuid; ...'`; the diff step fails if none exist |
| `realpath --relative-to` | `python3 os.path.relpath`; otherwise paths stay absolute |
| `python3` | Used only for UUID generation and relative paths |

## Models and providers

| Surface | Default | Source of truth |
| --- | --- | --- |
| opencode reviewer | `mistral/zai-glm-5-3#max` | `.opencode/agents/ponytail-review-readonly.md` frontmatter `model:` line |
| opencode e2e smoke tests | `mistral/zai-glm-5-3-flash` (no effort variant) | `E2E_MODEL` / `E2E_REASONING_EFFORT`, else the suite defaults |
| Mistral Vibe reviewer | alias `reviewer` → `zai-glm-5-3`, `thinking = "max"` | `.vibe/config.toml` `[[models]]` entry |

The opencode default is deliberately not hardcoded in `run-review.sh`: the script parses the agent's `model:` line, so the agent configuration and the orchestrator cannot drift apart. The Vibe agent uses an alias for the same reason; rename the preset alias and update `active_model`.

## Python and package tooling

- No Python application code, no `pyproject.toml`, no `requirements.txt`, no lockfile.
- `uvx` runs ephemeral tools; nothing is installed into the repository.
- `uvx reuse lint` is the compliance gate.
- `uvx --from skills-ref agentskills validate` is the authoritative Agent Skills check.
- `uvx strands-agents-sops skills` converts legacy SOP files.

## Third-party content inventory

| Upstream | License | Content in this repo | Status |
| --- | --- | --- | --- |
| `strands-agents/agent-sop` | Apache-2.0 | `skills/pdd`, `skills/codebase-summary`, `.agents/skills/agent-sop-author` | Modified derivatives |
| `DietrichGebert/ponytail` | MIT | `skills/ponytail-review`, `.opencode/agents/ponytail-review-readonly.md` | Verbatim skill; modified agent derivative |
| `agentskills/agentskills` | CC-BY-4.0 (docs) | `.agents/skills/agent-sop-author/assets/agent-skills-specification.md` | Verbatim published Markdown export |

Original demiourgoi content is MIT: the Makefile, installer logic, the `ponytail-review-pdd` and `edenai-zed-config` skills, the Vibe agent/config, tests, and this documentation.

## Environment and portability notes

- `compute-diff.sh` and `run-review.sh` must run inside a git work tree; they `cd` to the repository root before producing paths.
- The test suite uses GNU `sed -i` in `test-run-review.sh`; on macOS the in-place flag needs an argument (`sed -i ''`).
- `/proc/sys/kernel/random/uuid` is Linux-only; `uuidgen` and `python3` are the portable fallbacks.
- `make install` reads `PWD` from the environment; shells that do not export `PWD` require an explicit `TARGET_DIR`.
- Sandboxed `uvx` runs may need `UV_CACHE_DIR`, `UV_TOOL_DIR`, and `UV_TOOL_BIN_DIR` redirected to writable paths.
- Live e2e tests spend real model tokens and require opencode authentication; they are never part of the default test run.
