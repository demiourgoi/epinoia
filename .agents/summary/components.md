# Components

<!-- tags: components, responsibilities -->

## Component map

| Component | Responsibility | Key files |
| --- | --- | --- |
| `ponytail-review-pdd` skill | Orchestrates a read-only review of a PDD artifact | `skills/ponytail-review-pdd/SKILL.md`, `scripts/run-review.sh`, `scripts/compute-diff.sh` |
| `pdd` skill | Guides a project from rough idea to requirements, research, detailed design, and implementation plan | `skills/pdd/SKILL.md` |
| `codebase-summary` skill | Generates this knowledge base and a consolidated `AGENTS.md` | `skills/codebase-summary/SKILL.md` |
| `edenai-zed-config` skill | Generates one Zed `settings.json` model entry from Zed docs and the LiteLLM catalog | `skills/edenai-zed-config/SKILL.md` |
| `ponytail-review` skill | Upstream review methodology, shipped verbatim | `skills/ponytail-review/SKILL.md`, `LICENSE` |
| opencode reviewer | Read-only review agent and its permissions | `.opencode/agents/ponytail-review-readonly.md`, `.opencode/opencode.json`, `.opencode/agents/LICENSE` |
| Vibe reviewer | Equivalent read-only reviewer for Mistral Vibe | `.vibe/agents/ponytail-reviewer.toml`, `.vibe/config.toml` |
| `agent-sop-author` | Development skill that creates and validates new skills | `.agents/skills/agent-sop-author/SKILL.md`, `validate-skill.sh`, `assets/` |
| `update-third-party-notices` | Development skill that records reused third-party content | `.agents/skills/update-third-party-notices/SKILL.md` |
| SOP converter | Converts `*.sop.md` sources into an Agent Skills directory | `bin/agent-sop-to-skill.sh` |
| Installer | Copies skills and agent configs into a target project | `Makefile` (`install` target) |
| Test harness | Discovers and runs shell suites; provides assertions and fixtures | `tests/run.sh`, `tests/lib.sh`, `tests/skills/ponytail-review-pdd/lib.sh` |
| Test suites | Verify install placement, diff computation, orchestrator behavior, and live opencode permissions | `tests/test-install.sh`, `tests/skills/ponytail-review-pdd/test-*.sh` |
| Compliance artifacts | Record licenses, provenance, and per-file SPDX metadata | `LICENSES/`, `LICENSE`, `REUSE.toml`, `THIRD-PARTY-NOTICES.md` |

## Distributable skills (`skills/`)

### `ponytail-review-pdd`

The only component with executable orchestration. It reviews one of four subjects and writes an incrementally numbered review file:

| Subject | Reviewed artifact | Review file |
| --- | --- | --- |
| `tech-design` | `design/detailed-design.md` | `design/detailed-design-review-rev{J}.md` |
| `code-uncommitted` | staged + unstaged + untracked work against `HEAD` | `implementation/step-{I}-review-rev{J}.md` |
| `code-commits` | `git diff {start}..{end}` | `implementation/step-{I}-review-rev{J}.md` |
| `final-pdd-review` | the whole codebase against the PDD project | `summary-review-rev{J}.md` |

`run-review.sh` owns validation, diff orchestration, revision selection, prompt construction, and the opencode call. `compute-diff.sh` owns the two diff modes and excludes this skill's own review machinery from uncommitted diffs. The agent does the review itself.

### `pdd`

A prose SOP with no scripts. It defines the project directory layout (`rough-idea.md`, `idea-honing.md`, `research/`, `design/detailed-design.md`, `implementation/plan.md`, `summary.md`), one-question-at-a-time requirements clarification, research checkpoints, and a test-driven implementation plan whose steps must each be demoable.

### `codebase-summary`

A prose SOP that produces `.agents/summary/` (knowledge base) and a consolidated `AGENTS.md`. It requires Mermaid diagrams, consistency and completeness review, and preservation of the human-maintained Custom Instructions section.

### `edenai-zed-config`

A prose SOP with no scripts. It fetches Zed's schema and the LiteLLM catalog, maps catalog fields to Zed fields, and emits one JSON model entry. It deliberately downloads the multi-megabyte catalog to disk instead of into context.

### `ponytail-review`

The upstream review methodology, copied byte-identically from `DietrichGebert/ponytail` (MIT). It defines the review order (correct, safe, holds under load, tested, fast, lean) and the report format. It is not executed directly here; its derivative is the opencode agent's prompt.

## Agent definitions and configuration

### opencode reviewer

- `.opencode/agents/ponytail-review-readonly.md` — Markdown agent with frontmatter (`description`, `mode`, `model`) and the review prompt. It may write only the review file named by the task.
- `.opencode/opencode.json` — permission table for `agents.ponytail-review-readonly`. Edits and shell are denied by default; shell is allowed only for specific read-only git commands; reads, glob, grep, web fetch, and web search are allowed; subagents and questions are denied.
- `.opencode/agents/LICENSE` — MIT sidecar recording provenance and the modifications relative to the upstream skill.

### Vibe reviewer

- `.vibe/agents/ponytail-reviewer.toml` — Vibe agent that loads the `ponytail-review` skill by name, uses `active_model = "reviewer"`, enables only `read_file`, `todo`, `ask_user_question`, `skill`, `bash`, and `write_file`, and allows shell only for read-only discovery commands. It writes its report to `.review.md`.
- `.vibe/config.toml` — top-level `show_thinking_nodes` and the `reviewer` model preset: `zai-glm-5-3` via the built-in `mistral` provider, `thinking = "max"`, `max_context_length = 1000000`, `auto_compact_threshold = 800000`.

The Vibe agent references the model alias instead of hardcoding the model; changing the preset name or alias requires updating the agent's `active_model`.

## Development-only skills (`.agents/skills/`)

- `agent-sop-author` — teaches the SOP prompt structure (parameters, numbered steps, RFC 2119 constraints), requires deterministic logic in `scripts/`, and bundles the Agent Skills specification and `validate-skill.sh`.
- `update-third-party-notices` — the compliance checklist: verify the upstream license, add `LICENSES/<SPDX-ID>.txt`, keep verbatim copies byte-identical, add `LICENSE` sidecars for modified derivatives, update `THIRD-PARTY-NOTICES.md` and `REUSE.toml`, and finish with `uvx reuse lint`.

## Support tooling and tests

- `bin/agent-sop-to-skill.sh` runs `uvx strands-agents-sops skills` and copies the generated files into `skills/<name>/`, leaving the old `*.sop.md` files for manual review.
- `tests/lib.sh` provides `run`, `run_in`, `assert_*`, and `finish`; it stores command output in `$OUT_FILE` and the exit code in `$RC`.
- `tests/skills/ponytail-review-pdd/lib.sh` builds a deterministic fixture repository with two commits, staged/unstaged/untracked changes, a PDD project, a codebase summary index, and the installed opencode agent.
- `tests/run.sh` discovers every `test-*.sh` file, skips `test-e2e*` unless asked, and reports per-suite and aggregate results.
