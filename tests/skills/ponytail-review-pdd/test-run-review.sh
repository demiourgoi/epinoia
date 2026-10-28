#!/usr/bin/env bash
# Hermetic tests for skills/ponytail-review-pdd/scripts/run-review.sh:
# dry-run output, parameter validation, setup guards, revision numbering,
# model selector, and subdirectory invocation. No network, no opencode runs.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

SUBJ=.agents/planning/2026-10-26-demo

setup_repo

group "dry-run: happy paths"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design
assert_rc 0 "tech-design dry-run exits 0"
assert_grep "Review file:.*design/detailed-design-review-rev1\.md$" "tech-design review file is rev1"
assert_grep "^Review the technical design located at $SUBJ/design/detailed-design\.md\.$" "tech-design task names the design"
assert_grep "Write your review to $SUBJ/design/detailed-design-review-rev1\.md\.$" "tech-design prompt names the review file"
assert_grep "rough idea \($SUBJ/rough-idea\.md\)" "tech-design prompt stresses the rough idea"
assert_grep "requirements refined in $SUBJ/idea-honing\.md" "tech-design prompt stresses idea-honing.md"
assert_grep "Research notes are under $SUBJ/research\." "tech-design prompt stresses the research"
assert_grep "first read \.agents/summary/index\.md" "tech-design prompt points at the codebase summary index"
assert_grep "Model selector: mistral/zai-glm-5-3#max$" "default model selector is mistral/zai-glm-5-3#max"
assert_grep "Agent: *ponytail-review-readonly \(project: $TEST_REPO/\.opencode/agents/ponytail-review-readonly\.md\)$" "agent found in the project"
assert_missing "$P/design/detailed-design-review-rev1.md" "dry-run writes no review file"
assert_glob_empty "$P"/changes-*.diff "dry-run computes no diff"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-uncommitted --step 2
assert_rc 0 "code-uncommitted dry-run exits 0"
assert_grep "Review file:.*implementation/step-2-review-rev1\.md$" "code-uncommitted review file is step-2 rev1"
assert_grep "^Review the code <computed on the real run: \{project_dir\}/changes-<uuid>\.diff> corresponding to implementation step 2\.$" "code-uncommitted task names the diff placeholder"
assert_grep "taking into account implementation step 2" "code-uncommitted prompt names the step"
assert_grep "read the \"Step 2:\" section of the plan" "code-uncommitted prompt points at the plan step"
assert_grep "technical design \($SUBJ/design/detailed-design\.md\)" "code-uncommitted prompt stresses the tech design"
assert_missing "$P/implementation/step-2-review-rev1.md" "code-uncommitted dry-run writes no review file"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-commits --step 1 --start-commit HEAD~1 --end-commit HEAD
assert_rc 0 "code-commits dry-run exits 0"
assert_grep "Commit range: *HEAD~1\.\.HEAD$" "code-commits shows the commit range"
assert_grep "Review file:.*implementation/step-1-review-rev1\.md$" "code-commits review file is step-1 rev1"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-commits --step 1 --start-commit HEAD~1
assert_rc 0 "code-commits without end commit exits 0"
assert_grep "Commit range: *HEAD~1\.\.HEAD$" "end_commit defaults to HEAD"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject final-pdd-review
assert_rc 0 "final-pdd-review dry-run exits 0"
assert_grep "^Review if this codebase is a sound and complete implementation of the requirements and tech design specified in $SUBJ\.$" "final-pdd-review task names the PDD project"
assert_grep "Review file:.*summary-review-rev1\.md$" "final-pdd-review review file is summary rev1"
assert_grep "the technical design \($SUBJ/design/detailed-design\.md\)" "final-pdd-review prompt stresses the tech design"

group "revision numbering"

touch "$P/design/detailed-design-review-rev1.md" "$P/design/detailed-design-review-rev2.md"
run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design
assert_rc 0 "tech-design dry-run with existing reviews exits 0"
assert_grep "Review file:.*design/detailed-design-review-rev3\.md$" "tech-design review revision increments to rev3"

touch "$P/implementation/step-2-review-rev1.md"
run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-uncommitted --step 2
assert_grep "Review file:.*implementation/step-2-review-rev2\.md$" "step review revision increments to rev2"

group "model selector"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design --model mistral/zai-glm-5-3-flash --reasoning-effort ""
assert_rc 0 "model override dry-run exits 0"
assert_grep "Model selector: mistral/zai-glm-5-3-flash$" "empty reasoning effort omits the #variant"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design --model test/model --reasoning-effort high
assert_grep "Model selector: test/model#high$" "reasoning effort is appended as #variant"

group "parameter validation"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject bogus
assert_rc 1 "invalid subject exits 1"
assert_grep "invalid --subject 'bogus'" "invalid subject error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-uncommitted
assert_rc 1 "code-uncommitted without step exits 1"
assert_grep "--step is required" "code-uncommitted without step error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-uncommitted --step 99
assert_rc 1 "nonexistent step exits 1"
assert_grep "no 'Step 99:' heading" "nonexistent step error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-uncommitted --step 0
assert_rc 1 "step 0 exits 1"
assert_grep "must be a positive integer" "step 0 error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-uncommitted --step abc
assert_rc 1 "non-numeric step exits 1"
assert_grep "must be a positive integer" "non-numeric step error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design --step 1
assert_rc 1 "step with tech-design exits 1"
assert_grep "--step does not apply to --subject tech-design" "step with tech-design error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject final-pdd-review --step 1
assert_rc 1 "step with final-pdd-review exits 1"
assert_grep "--step does not apply to --subject final-pdd-review" "step with final-pdd-review error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design --start-commit HEAD~1
assert_rc 1 "start-commit with tech-design exits 1"
assert_grep "only apply to --subject code-commits" "start-commit with tech-design error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject code-uncommitted --step 1 --end-commit HEAD
assert_rc 1 "end-commit with code-uncommitted exits 1"
assert_grep "only apply to --subject code-commits" "end-commit with code-uncommitted error message"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir missing-project-dir --subject tech-design
assert_rc 1 "missing project dir exits 1"
assert_grep "project directory not found" "missing project dir error message"

group "opencode setup guards"

# A repository without any agent must fail. Use a /tmp fixture so the
# ancestor walk cannot find an agent installed above the test workspace, and
# point XDG_CONFIG_HOME at an empty directory so a globally installed agent
# cannot interfere either.
MISSING=/tmp/ponytail-review-pdd-missing-agent
rm -rf "$MISSING"
mkdir -p "$MISSING/proj/design"
printf '# Design\nNo agent here\n' > "$MISSING/proj/design/detailed-design.md"
git -C "$MISSING" init -q
run_in "$MISSING" env XDG_CONFIG_HOME="$MISSING/xdg" "$SKILL_DIR/scripts/run-review.sh" \
    --dry-run --project-dir "$MISSING/proj" --subject tech-design
assert_rc 1 "missing agent file exits 1"
assert_grep "is not installed for this repository" "missing agent file error message"

mv "$TEST_REPO/.opencode/opencode.json" "$WORK_DIR/opencode.json.bak"
run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design
assert_rc 1 "agent without permissions config exits 1"
assert_grep "no read-only permissions configured" "agent without permissions error message"
mv "$WORK_DIR/opencode.json.bak" "$TEST_REPO/.opencode/opencode.json"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design
assert_rc 0 "restored setup works again"

group "monorepo layout: agent at the git root, project in a package"

# The harold-mcp shape: the package is a subdirectory of its git repository
# and the agent is installed at the repository root.
MONO=/tmp/ponytail-review-pdd-monorepo
rm -rf "$MONO"
mkdir -p "$MONO/pkg/.agents/planning/p/design" "$MONO/.opencode/agents"
git -C "$MONO" init -q
printf '# Design\nMonorepo design\n' > "$MONO/pkg/.agents/planning/p/design/detailed-design.md"
cp "$REPO_ROOT/.opencode/agents/ponytail-review-readonly.md" "$MONO/.opencode/agents/"
cp "$REPO_ROOT/.opencode/opencode.json" "$MONO/.opencode/"

run_in "$MONO/pkg" "$SKILL_DIR/scripts/run-review.sh" --dry-run \
    --project-dir "$MONO/pkg/.agents/planning/p" --subject tech-design
assert_rc 0 "monorepo package review starts when the agent is at the git root"
assert_grep "Agent: *ponytail-review-readonly \(project: $MONO/\.opencode/agents/ponytail-review-readonly\.md\)$" "monorepo finds the agent at the git root"
assert_grep "Review file:.*detailed-design-review-rev1\.md$" "monorepo resolves the review file"

group "opencode walk: agent installed above the git root"

OUTER=/tmp/ponytail-review-pdd-ancestor
INNER="$OUTER/inner"
rm -rf "$OUTER"
mkdir -p "$INNER/proj/design" "$OUTER/.opencode/agents"
git -C "$OUTER" init -q
git -C "$INNER" init -q
printf '# Design\nAncestor design\n' > "$INNER/proj/design/detailed-design.md"
cp "$REPO_ROOT/.opencode/agents/ponytail-review-readonly.md" "$OUTER/.opencode/agents/"
cp "$REPO_ROOT/.opencode/opencode.json" "$OUTER/.opencode/"

run_in "$INNER" "$SKILL_DIR/scripts/run-review.sh" --dry-run \
    --project-dir "$INNER/proj" --subject tech-design
assert_rc 0 "agent found above the git root"
assert_grep "Agent: *ponytail-review-readonly \(project: $OUTER/\.opencode/agents/ponytail-review-readonly\.md\)$" "ancestor walk finds the agent above the git root"

group "invocation from a subdirectory"

run_in "$TEST_REPO/sub/dir" "$SKILL_DIR/scripts/run-review.sh" --dry-run \
    --project-dir ../../.agents/planning/2026-10-26-demo --subject tech-design
assert_rc 0 "subdirectory invocation exits 0"
assert_grep "Review file:.*design/detailed-design-review-rev3\.md$" "subdirectory invocation resolves the review file"
assert_grep "^Review the technical design located at $SUBJ/design/detailed-design\.md\.$" "subdirectory invocation produces repository-relative paths"

group "real run with a stubbed opencode"

# A fake opencode on PATH records the exact arguments run-review.sh execs and
# writes the review file the script expects, so the full execution path
# (validation -> diff -> review file -> launch -> report) is covered without
# spending tokens on a real model. The console transcript lands in the .log
# file, and the script prints the review file content as its report.
mkdir -p "$WORK_DIR/bin"
cat > "$WORK_DIR/bin/opencode" <<STUB
#!/usr/bin/env bash
printf 'arg: %s\n' "\$@"
mkdir -p "$P/implementation"
printf 'What this does:\nStub review report.\n' > "$P/implementation/step-1-review-rev1.md"
STUB
chmod +x "$WORK_DIR/bin/opencode"

run env PATH="$WORK_DIR/bin:$PATH" "$SKILL_DIR/scripts/run-review.sh" \
    --project-dir "$SUBJ" --subject code-uncommitted --step 1 \
    --model test/model --reasoning-effort high
LOG="$P/implementation/step-1-review-rev1.log"
assert_rc 0 "real run against the stub exits 0"
assert_file_grep "^arg: --agent$" "$LOG" "passes --agent to opencode"
assert_file_grep "^arg: ponytail-review-readonly$" "$LOG" "selects the reviewer agent"
assert_file_grep "^arg: --model$" "$LOG" "passes --model to opencode"
assert_file_grep "^arg: test/model#high$" "$LOG" "passes the composed model selector"
assert_file_grep "^arg: Review the code .*changes-.*\.diff corresponding to implementation step 1\.$" "$LOG" "passes the review task as the prompt"
assert_file_grep "Write your review to $SUBJ/implementation/step-1-review-rev1\.md" "$LOG" "prompt names the review file"
assert_grep "What this does:" "prints the review file content"
assert_grep "Review written to $P/implementation/step-1-review-rev1\.md" "reports where the review was written"
assert_glob_nonempty "$P"/changes-*.diff "real run computes the diff"

group "usage"

run "$SKILL_DIR/scripts/run-review.sh" --help
assert_rc 0 "run-review.sh --help exits 0"
assert_grep "Usage: run-review\.sh" "--help prints usage"

echo
echo "Test workspace (kept for inspection): $WORK_DIR"
finish
