#!/usr/bin/env bash
# Live smoke tests for ponytail-review-pdd's opencode integration.
#
# Deliberately cheap: tiny prompts, the cheapest default model, no review
# work, so a run costs a few cents at most. They need opencode
# authentication, so the runner only executes them with --e2e (see
# tests/run.sh).
#
# What is NOT automated here: a full review. A real review spends serious
# reasoning money, so it is not part of the test suite; the full
# run-review.sh execution path is covered hermetically by the stubbed
# opencode test instead (see test-run-review.sh). To exercise a real review,
# run the skill itself against a real project.
#
# The model defaults to edenai/zai/glm-5.3-flash; override with the E2E_MODEL
# and E2E_REASONING_EFFORT environment variables.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

E2E_MODEL="${E2E_MODEL:-edenai/zai/glm-5.3-flash}"
E2E_EFFORT="${E2E_REASONING_EFFORT:-}"   # default: no variant

SELECTOR="$E2E_MODEL"
if [[ -n "$E2E_EFFORT" ]]; then
    SELECTOR="$SELECTOR#$E2E_EFFORT"
fi

echo "e2e model selector: $SELECTOR (override with E2E_MODEL / E2E_REASONING_EFFORT)"

if ! command -v opencode >/dev/null 2>&1; then
    echo "FAIL opencode is required for the e2e suite but not installed" >&2
    exit 1
fi

setup_repo

group "e2e: opencode runs the reviewer agent"

run_in "$TEST_REPO" opencode run --agent ponytail-review-readonly --model "$SELECTOR" \
    "Reply with exactly: SMOKE OK"
assert_rc 0 "opencode run with the reviewer agent completes"
assert_grep "ponytail-review-readonly" "the reviewer agent was used"
assert_grep "SMOKE OK" "the model replied"

group "e2e: read-only enforcement (agent permissions)"

POLICY_PROMPT="This is a permissions verification, not a code review. Your review report for this task is exactly the words 'policy ok': write them to the file 'e2e-policy-review-rev1.md' in the repository root — that is the review file named by this task, and writing it is allowed. Then verify the read-only enforcement by actually attempting, and reporting the outcome of: (1) the shell command 'touch forbidden-test.txt'; (2) creating a file named 'notallowed.txt' with your file-writing tool. Keep every reply to one short line."

run_in "$TEST_REPO" opencode run --agent ponytail-review-readonly --model "$SELECTOR" "$POLICY_PROMPT"
assert_rc 0 "opencode permissions-check run completes"
assert_missing "$TEST_REPO/forbidden-test.txt" "mutating shell commands are blocked"
assert_missing "$TEST_REPO/notallowed.txt" "writing files other than review files is blocked"
assert_nonempty "$TEST_REPO/e2e-policy-review-rev1.md" "writing the review file is allowed"
assert_file_grep "policy ok" "$TEST_REPO/e2e-policy-review-rev1.md" "review file has the requested content"

echo
echo "Test workspace (kept for inspection): $WORK_DIR"
finish
