---
name: ponytail-review-pdd
description: Reviews artifacts created by the pdd skill (Prompt-Driven Development) by delegating to the read-only ponytail-review-readonly opencode agent. Reviews a technical design (design/detailed-design.md), the code of an implementation plan step (uncommitted changes or a commit-range diff), or the complete implementation of a PDD project against its requirements and tech design. Each review is written to an incrementally numbered review file (rev1, rev2, ...). Use when asked to review, check, or audit a PDD design, implementation step code, or a finished PDD project.
metadata:
  version: "1.0.0"
---

# Ponytail Review for PDD

## Overview

This skill reviews artifacts produced by the `pdd` skill and prints the review.
The review itself is performed by the read-only opencode agent
`ponytail-review-readonly`, launched non-interactively with `opencode run`.
The agent reads the artifact plus its PDD context, writes a markdown review to
a review file, and returns the same report as its response, which this SOP
presents as its result.

Review subjects and review files (the revision `{J}` starts at 1 and
increments by 1 whenever a previous review file already exists, so an artifact
can be re-reviewed after fixes):

| review_subject | What is reviewed | Review file |
| --- | --- | --- |
| `tech-design` | `{project_dir}/design/detailed-design.md` | `{project_dir}/design/detailed-design-review-rev{J}.md` |
| `code-uncommitted` | all uncommitted work (tracked staged + unstaged changes against HEAD, plus untracked files) | `{project_dir}/implementation/step-{I}-review-rev{J}.md` |
| `code-commits` | `git diff {start_commit}..{end_commit}` | `{project_dir}/implementation/step-{I}-review-rev{J}.md` |
| `final-pdd-review` | the whole codebase against the PDD project | `{project_dir}/summary-review-rev{J}.md` |

For code reviews the diff is computed first and saved as
`{project_dir}/changes-{UUID}.diff`; the agent reviews that file.

Prerequisites (the scripts check them and report how to fix them):

- `git` and `opencode` are installed, and opencode is authenticated for the
  model's provider.
- The opencode agent is installed in the repository being reviewed as
  `.opencode/agents/ponytail-review-readonly.md`, together with the
  `.opencode/opencode.json` that defines its read-only permissions (all of it
  lives in the epinoia repository's `.opencode/` directory).

## Parameters

- **project_dir** (required): base directory of the PDD project to review; contains `rough-idea.md`, `idea-honing.md`, `research/`, `design/detailed-design.md`, and `implementation/plan.md`. Relative to the current directory or absolute
- **review_subject** (required): what to review; one of `tech-design`, `code-uncommitted`, `code-commits`, `final-pdd-review`
- **implementation_step** (optional): implementation plan step number the code belongs to. Required when review_subject is `code-uncommitted` or `code-commits`; invalid for the other subjects
- **start_commit** (optional): first commit of the range to review. Required when review_subject is `code-commits`; invalid otherwise
- **end_commit** (optional, default: "HEAD"): last commit of the range to review. Only valid when review_subject is `code-commits`
- **model** (optional, default: "edenai/zai/glm-5.3"): opencode model in `provider/model` form (e.g. "edenai/zai/glm-5.3"); combined with reasoning_effort as `provider/model#reasoning_effort`
- **reasoning_effort** (optional, default: "max"): opencode reasoning-effort variant appended to the model selector (e.g. "max", "high"); pass an empty string to use the model without a variant

**Constraints for parameter acquisition:**
- If all required parameters are already provided, You MUST proceed to the Steps
- If any required parameters are missing, You MUST ask for them before proceeding
- When asking for parameters, You MUST request all parameters in a single prompt
- When asking for parameters, You MUST use the exact parameter names as defined
- You MUST NOT ask for optional parameters, because they all have defaults; You SHOULD accept them only when the user provides them explicitly
- You MUST support multiple input methods including:
  - Direct input: parameters given in the conversation
  - File path: a path to the PDD project directory
- You MUST confirm successful acquisition of all parameters before proceeding

## Steps

### 1. Validate the request and preview the review

Run the validation dry-run of the orchestration script with all parameters:

```bash
{skill_dir}/scripts/run-review.sh --dry-run \
  --project-dir <project_dir> --subject <review_subject> \
  [--step <implementation_step>] \
  [--start-commit <start_commit>] [--end-commit <end_commit>] \
  [--model <model>] [--reasoning-effort <reasoning_effort>]
```

The script validates the subject, the parameter combinations (implementation
step for code reviews, commit range for `code-commits`), the PDD artifacts
(detailed design for `tech-design`, implementation plan and a matching
`Step {I}:` heading for code reviews), and the opencode setup. It prints the
resolved review file, the diff file, the codebase summary detection, the model
selector, and the exact prompt that will be sent to the reviewer agent.

**Constraints:**
- You MUST run the script with `--dry-run` before the real run, because it shows exactly what will be reviewed and catches setup errors before anything is launched
- You MUST pass the parameters exactly as acquired, mapping them to the script flags
- If validation fails, You MUST report the script's error to the user and ask for corrected parameters in a single prompt; You MUST NOT proceed to Step 2
- You MUST NOT modify the prompt the script builds, because it is part of the reviewed contract with the reviewer agent
- You SHOULD tell the user the review file path that will be used, because re-reviews increment the revision number
- You MAY skip this step for repeated identical invocations within the same conversation, because validation results do not change

### 2. Run the opencode review

Run the same command without `--dry-run`. The script computes the diff for
code subjects (saving `{project_dir}/changes-{UUID}.diff`), picks the next
free review revision, and launches
`opencode run --agent ponytail-review-readonly --model <model>#<reasoning_effort> <prompt>`.
The reviewer is read-only except for the review file, enforced both by its
prompt and by its opencode permissions.

**Constraints:**
- You MUST run the command with a timeout of at least 600000 ms (10 minutes), because the reviewer at max reasoning effort reads a lot of context and can take several minutes
- You MUST NOT add `--auto` or any extra flags to the opencode invocation, because the script already passes exactly what is needed and `--auto` would weaken the read-only permission enforcement
- You MUST NOT run the opencode agent yourself with a hand-written prompt, because the script is the reviewed source of truth for the prompt, paths, and model
- If the command fails, You MUST report the full error; You MUST NOT retry more than once without asking the user
- You MUST NOT touch the generated diff or review files yourself, because they are the reviewer's inputs and outputs

### 3. Present the review result

The script's stdout is the reviewer's response: the full review report (the
same content it wrote to the review file).

**Constraints:**
- You MUST print the reviewer's response in full, because the response is the result of this SOP
- You MUST point the user to the review file path that was written
- You SHOULD highlight the verdict (for example `Verdict: Ship.` or `Verdict: fix 1 and 3 first.`) and the "Must fix" findings when summarizing
- You MUST NOT modify the review or implement its findings unless the user explicitly asks, because applying fixes is outside this SOP

## Examples

### Example 1: Technical design review

**Input:**
- project_dir: ".agents/planning/2026-10-20-eval-tool"
- review_subject: "tech-design"

**Expected Behavior:**
The agent validates the design exists, then the script launches the reviewer
with the default model (`edenai/zai/glm-5.3#max`). The reviewer reads
`design/detailed-design.md`, the rough idea, `idea-honing.md`, and the
research notes, and writes `design/detailed-design-review-rev1.md`. Its
response (the report) is printed as the result.

### Example 2: Review uncommitted code for step 3

**Input:**
- project_dir: ".agents/planning/2026-10-20-eval-tool"
- review_subject: "code-uncommitted"
- implementation_step: 3

**Expected Behavior:**
The script saves all uncommitted work (staged + unstaged + untracked) to
`{project_dir}/changes-{UUID}.diff`, and the reviewer checks that diff
against the design and the "Step 3:" section of `implementation/plan.md`,
writing `implementation/step-3-review-rev1.md`. After the user fixes the code,
re-running with the same parameters produces `step-3-review-rev2.md`.

### Example 3: Review a commit range for step 4

**Input:**
- project_dir: ".agents/planning/2026-10-20-eval-tool"
- review_subject: "code-commits"
- implementation_step: 4
- start_commit: "HEAD~2"
- end_commit: "HEAD"

**Expected Behavior:**
Same as Example 2, but the diff is `git diff HEAD~2..HEAD`, saved to
`changes-{UUID}.diff`. Omitting end_commit defaults it to "HEAD".

### Example 4: Final PDD review

**Input:**
- project_dir: ".agents/planning/2026-10-20-eval-tool"
- review_subject: "final-pdd-review"

**Expected Behavior:**
The reviewer checks the whole codebase against the rough idea, the
requirements in `idea-honing.md`, the technical design, and the implementation
plan, writing `summary-review-rev1.md`.

### Example 5: Review with a different model

**Input:**
- project_dir: ".agents/planning/2026-10-20-eval-tool"
- review_subject: "code-uncommitted"
- implementation_step: 2
- model: "edenai/zai/glm-5.3-flash"
- reasoning_effort: ""

**Expected Behavior:**
Same as Example 2, but the reviewer runs with
`--model edenai/zai/glm-5.3-flash` (no reasoning-effort variant).

## Troubleshooting

### The script reports the opencode agent is not installed
The repository being reviewed must contain
`.opencode/agents/ponytail-review-readonly.md` and `.opencode/opencode.json`
with its read-only permissions. Copy the epinoia repository's `.opencode/`
directory into the repository being reviewed, or run
`make -C /path/to/epinoia install` from the repository to install into it
(which also installs the skills), and retry.

### opencode fails with a model or auth error
Check the model id with `opencode models` and authenticate the provider with
`opencode auth login`. An "Variant unavailable" error means the model does not
offer that reasoning-effort variant; choose another one (for example `high`).

### The command times out
Re-run with a longer timeout. If the review file was already written before
the timeout, inspect it before re-running; re-running creates the next
revision (rev{J+1}) only when a previous review file exists.

### code-uncommitted fails with "no changes to review"
The working tree has no uncommitted changes. Use `code-commits` with an
explicit range instead, or make the changes first.

### The review file is not written
Keep the PDD project inside the repository: the reviewer may only write
review files inside the project it reviews, and paths outside the repository
can be blocked by its permissions. The script also warns when project_dir is
the repository root.

### Parameters are rejected as invalid combinations
`implementation_step` applies only to `code-uncommitted`/`code-commits`;
`start_commit`/`end_commit` apply only to `code-commits`. The step must exist
as a `Step {I}:` heading in `implementation/plan.md`.
