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
assert_grep "Model selector: edenai/zai/glm-5\.3#max$" "default model selector is edenai/zai/glm-5.3#max"
assert_grep "Agent: *ponytail-review-readonly \(project\)$" "agent found in the project"
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

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design --model edenai/zai/glm-5.3-flash --reasoning-effort ""
assert_rc 0 "model override dry-run exits 0"
assert_grep "Model selector: edenai/zai/glm-5\.3-flash$" "empty reasoning effort omits the #variant"

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

mv "$TEST_REPO/.opencode/agents/ponytail-review-readonly.md" "$WORK_DIR/agent.md.bak"
run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design
assert_rc 1 "missing agent file exits 1"
assert_grep "ponytail-review-readonly' is not installed in this project" "missing agent file error message"
mv "$WORK_DIR/agent.md.bak" "$TEST_REPO/.opencode/agents/ponytail-review-readonly.md"

mv "$TEST_REPO/.opencode/opencode.json" "$WORK_DIR/opencode.json.bak"
run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design
assert_rc 1 "agent without permissions config exits 1"
assert_grep "no read-only permissions configured" "agent without permissions error message"
mv "$WORK_DIR/opencode.json.bak" "$TEST_REPO/.opencode/opencode.json"

run "$SKILL_DIR/scripts/run-review.sh" --dry-run --project-dir "$SUBJ" --subject tech-design
assert_rc 0 "restored setup works again"

group "invocation from a subdirectory"

run_in "$TEST_REPO/sub/dir" "$SKILL_DIR/scripts/run-review.sh" --dry-run \
    --project-dir ../../.agents/planning/2026-10-26-demo --subject tech-design
assert_rc 0 "subdirectory invocation exits 0"
assert_grep "Review file:.*design/detailed-design-review-rev3\.md$" "subdirectory invocation resolves the review file"
assert_grep "^Review the technical design located at $SUBJ/design/detailed-design\.md\.$" "subdirectory invocation produces repository-relative paths"

group "real run with a stubbed opencode"

# A fake opencode on PATH records the exact arguments run-review.sh execs, so
# the full execution path (validation -> diff -> review file -> launch) is
# covered without spending tokens on a real model.
mkdir -p "$WORK_DIR/bin"
cat > "$WORK_DIR/bin/opencode" <<'STUB'
#!/usr/bin/env bash
printf 'arg: %s\n' "$@"
STUB
chmod +x "$WORK_DIR/bin/opencode"

run env PATH="$WORK_DIR/bin:$PATH" "$SKILL_DIR/scripts/run-review.sh" \
    --project-dir "$SUBJ" --subject code-uncommitted --step 1 \
    --model test/model --reasoning-effort high
assert_rc 0 "real run against the stub exits 0"
assert_grep "arg: --agent$" "passes --agent to opencode"
assert_grep "arg: ponytail-review-readonly$" "selects the reviewer agent"
assert_grep "arg: --model$" "passes --model to opencode"
assert_grep "arg: test/model#high$" "passes the composed model selector"
assert_grep "^arg: Review the code .*changes-.*\.diff corresponding to implementation step 1\.$" "passes the review task as the prompt"
assert_grep "Write your review to $SUBJ/implementation/step-1-review-rev1\.md" "prompt names the review file"
assert_grep "Review file: $P/implementation/step-1-review-rev1\.md" "prints the review file before launching"
assert_glob_nonempty "$P"/changes-*.diff "real run computes the diff"

group "usage"

run "$SKILL_DIR/scripts/run-review.sh" --help
assert_rc 0 "run-review.sh --help exits 0"
assert_grep "Usage: run-review\.sh" "--help prints usage"

echo
echo "Test workspace (kept for inspection): $WORK_DIR"
finish
