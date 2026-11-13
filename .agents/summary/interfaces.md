# Interfaces

<!-- tags: interfaces, cli, contracts -->

## Command-line interfaces

### `skills/ponytail-review-pdd/scripts/run-review.sh`

The main orchestration entry point. It validates the request, computes the diff for code subjects, selects the next review revision, builds the prompt, and launches opencode.

```text
run-review.sh --project-dir DIR --subject SUBJECT [options]

Required:
  --project-dir DIR     PDD project directory
  --subject SUBJECT     tech-design | code-uncommitted | code-commits | final-pdd-review

Options:
  --step N              implementation plan step (required for code subjects, invalid otherwise)
  --start-commit REF    first commit of the range (required for code-commits)
  --end-commit REF      last commit of the range (default HEAD; code-commits only)
  --model MODEL         opencode model in provider/model form (default: agent frontmatter)
  --reasoning-effort E  variant appended as #E (default: agent frontmatter; empty = no variant)
  --dry-run             validate and print the plan and prompt without side effects
  -h, --help            print usage
```

Contract:

- **Exit 0** — success (`--dry-run` prints the resolved plan; a real run prints the review report).
- **Exit 1** — any validation, setup, or opencode failure. Errors go to stderr.
- **Stdout on a real run** — only the review file content. Everything else (review/diff/log paths, heartbeats, errors) goes to stderr.
- **Side effects on a real run** — writes `{project_dir}/changes-{UUID}.diff` for code subjects, writes/overwrites `{review_file}` via opencode, and writes `{review_file base}.log` with the full transcript.
- **Side effects on `--dry-run`** — none; no diff is computed and no review file is created.

Validation performed before any side effect:

- subject is one of the four values;
- `--step` only with code subjects and a positive integer;
- `--start-commit`/`--end-commit` only with `code-commits`, and `--start-commit` is mandatory there;
- project directory exists;
- `design/detailed-design.md` exists for `tech-design` and `final-pdd-review`;
- `implementation/plan.md` exists and contains a `Step {I}:` heading for code subjects;
- `git` and `opencode` are installed and the current directory is inside a git work tree;
- the reviewer agent is installed at or above the git root, and its read-only permissions are configured (project agent only).

### `skills/ponytail-review-pdd/scripts/compute-diff.sh`

```text
compute-diff.sh --mode uncommitted --out FILE
compute-diff.sh --mode commits --start REF --end REF --out FILE
```

- Prints the diff file path on success.
- `uncommitted` includes tracked changes against `HEAD` (staged + unstaged) and untracked files as new-file diffs.
- Excludes review machinery: `changes-*.diff`, `*-review-rev*.md`, and `*-review-rev*.log`.
- `commits` requires both refs, verifies they resolve to commits, and writes `git diff START..END`.
- Exit 1 on errors (missing git, not a work tree, unknown refs, empty diff); exit 2 on missing `--mode`/`--out`. An empty diff removes the output file and fails.

### `bin/agent-sop-to-skill.sh`

```text
agent-sop-to-skill.sh <skill-name>
```

Runs `uvx strands-agents-sops skills --sop-paths skills/<name> --output-dir <temp>` and copies the generated tree into `skills/<name>/`, overwriting existing generated files. Leaves `*.sop.md` sources in place and prints a reminder about `SKILL.md` review, LICENSE sidecars, and notices. Exit 2 on wrong argument count, 1 when the skill directory is missing.

### `.agents/skills/agent-sop-author/validate-skill.sh`

```text
validate-skill.sh <path-to-skill-directory>
```

Checks: `SKILL.md` exists; YAML frontmatter is present; `name` and `description` exist; `name` matches the directory, uses kebab-case, and is at most 64 characters; `description` is at most 1024 characters; Overview, Parameters, Steps, numbered sub-steps, and Constraints sections exist; RFC 2119 keywords appear. It then runs the authoritative `uvx --from skills-ref agentskills validate <dir>`. Exit 0 only when there are no errors (warnings are allowed).

### `make` targets

| Target | Interface |
| --- | --- |
| `make install` | `TARGET_DIR` selects the destination (default: caller's `PWD`). Copies `skills/` to `TARGET_DIR/.agents/skills/`, `.opencode/` to the git root of `TARGET_DIR`, and `.vibe/` to `TARGET_DIR`. Exits 2 for missing/self targets. |
| `make test` | Runs `tests/run.sh` (hermetic suites only). |
| `make test-e2e` | Runs `tests/run.sh --e2e` (hermetic plus live opencode smoke tests). |
| `make help` | Lists targets parsed from the Makefile comments. |

### `tests/run.sh`

```text
tests/run.sh              # hermetic suites
tests/run.sh --e2e        # hermetic plus e2e
tests/run.sh --e2e-only   # only e2e
tests/run.sh --help
```

Exit 0 when every selected suite passes; 1 when any fails or no suites exist; 2 on unknown options. A suite is any `test-*.sh` file under `tests/`; basenames starting with `test-e2e` are treated as live tests.

## Agent interfaces

### opencode agent contract

`.opencode/agents/ponytail-review-readonly.md` frontmatter:

| Field | Value |
| --- | --- |
| `description` | Read-only reviewer for PDD artifacts; writes only its review file |
| `mode` | `primary` |
| `model` | `mistral/zai-glm-5-3#max` (the single source of truth for `run-review.sh`) |

Invocation contract: `opencode run --agent ponytail-review-readonly --model <selector> <prompt>`. The script passes the prompt as one argument; it never adds `--auto`, `--thinking`, or log flags.

The prompt always contains the review task, the review file path, the PDD project path, the relevant context files, and the statement that all paths are relative to the repository root.

### opencode permissions contract

`.opencode/opencode.json` defines an ordered permission table under `agents.ponytail-review-readonly.permissions`. Each entry is `{action, resource, effect}`:

- **edit** — denied for `*`, allowed for `*-review-rev*.md`.
- **shell** — denied for `*`, allowed only for explicit read-only git subcommands.
- **read** — allowed, except `*.env`/`*.env.*` ask; `*.env.example` allowed.
- **glob/grep/webfetch/websearch/external_directory** — allowed.
- **subagent/execute/question** — denied.

`run-review.sh` considers the agent configured if this file names the agent, or if the agent Markdown has a `permissions:` frontmatter block.

### Vibe agent contract

`.vibe/agents/ponytail-reviewer.toml` uses the top-level agent keys:

| Field | Value |
| --- | --- |
| `agent_type` | `agent` |
| `display_name` | `Ponytail reviewer` |
| `description` | Read-only agent for code and tech design reviews |
| `instructions` | Loads the `ponytail-review` skill; forbids edits except `.review.md` |
| `safety` | `neutral` |
| `enabled_tools` | `read_file`, `todo`, `ask_user_question`, `skill`, `bash`, `write_file` |
| `active_model` | `reviewer` (resolves to the `[[models]]` alias in `.vibe/config.toml`) |

Tool blocks:

- `[tools.bash]` — `permission = "ask"`, an allowlist of read-only discovery commands, and a denylist that blocks mutation and file-slicing/search commands (`cat`, `grep`, `sed`, `awk`, `rm`, …).
- `[tools.write_file]` — `permission = "ask"`, allowlist `**/.review.md`, `outside_workdir = "deny"`.

### Vibe model preset contract

`.vibe/config.toml` declares one `[[models]]` entry: `name = "zai-glm-5-3"`, `provider = "mistral"`, `alias = "reviewer"`, `thinking = "max"`, `max_context_length = 1000000`, `auto_compact_threshold = 800000`. The agent references the alias, not the model name.

## File contracts

- **PDD project**: `rough-idea.md`, `idea-honing.md`, `research/`, `design/detailed-design.md`, `implementation/plan.md`, `summary.md`.
- **Review files**: `design/detailed-design-review-rev{J}.md`, `implementation/step-{I}-review-rev{J}.md`, `summary-review-rev{J}.md`; `{J}` starts at 1 and is the first free revision.
- **Transcripts**: same path as the review file with `.md` replaced by `.log`.
- **Diffs**: `{project_dir}/changes-{UUID}.diff`.
- **Codebase summary**: the review script looks for `{project_dir}/../../summary/index.md` and, when present, tells the reviewer to read it first.
- **Skill directories**: `skills/<name>/SKILL.md` with matching frontmatter `name`; deterministic logic in `scripts/`.

## Environment variables

| Variable | Used by |
| --- | --- |
| `TARGET_DIR` | `make install` destination |
| `PWD` | Default `TARGET_DIR`; also used by tests to simulate an outside-repository install |
| `XDG_CONFIG_HOME` | Fallback location for a globally installed opencode agent |
| `E2E_MODEL`, `E2E_REASONING_EFFORT` | Live opencode smoke tests |
| `UV_CACHE_DIR`, `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR` | Sandboxed `uvx` runs (documented in the validation and compliance skills) |
