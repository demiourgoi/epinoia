#!/usr/bin/env bash
# Hermetic tests for skills/ponytail-review-pdd/scripts/compute-diff.sh:
# uncommitted mode (tracked + staged + untracked, artifact exclusion),
# commits mode, and guards. No network, no opencode runs.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

setup_repo

group "uncommitted mode"

run "$SKILL_DIR/scripts/compute-diff.sh" --mode uncommitted --out "$P/changes-test.diff"
assert_rc 0 "uncommitted diff exits 0"
assert_grep "^$P/changes-test\.diff$" "prints the diff file path"
assert_file_grep "^diff --git a/base\.txt" "$P/changes-test.diff" "contains the tracked modification"
assert_file_grep "^\+hello v3 uncommitted" "$P/changes-test.diff" "contains the unstaged content"
assert_file_grep "^diff --git a/stagedfile\.txt" "$P/changes-test.diff" "contains the staged new file"
assert_file_grep "^\+staged content" "$P/changes-test.diff" "contains the staged content"
assert_file_grep "^diff --git a/newfile\.txt" "$P/changes-test.diff" "contains the untracked file"
assert_file_grep "^\+new untracked" "$P/changes-test.diff" "contains the untracked content"
assert_file_grep "^diff --git a/\.opencode/agents/ponytail-review-readonly\.md" "$P/changes-test.diff" "contains the untracked agent installation files"
assert_file_not_grep "^diff --git .*changes-test\.diff" "$P/changes-test.diff" "the diff does not include itself"

group "review artifacts are excluded from uncommitted diffs"

printf 'stale diff\n' > "$P/changes-stale.diff"
printf 'stale review\n' > "$P/implementation/step-9-review-rev1.md"
printf 'stale transcript\n' > "$P/implementation/step-9-review-rev1.log"
printf 'stale review\n' > "$P/design/detailed-design-review-rev1.md"

run "$SKILL_DIR/scripts/compute-diff.sh" --mode uncommitted --out "$P/changes-test2.diff"
assert_rc 0 "uncommitted diff with stale artifacts exits 0"
assert_file_not_grep "^diff --git .*changes-" "$P/changes-test2.diff" "no changes-*.diff artifacts included"
assert_file_not_grep "^diff --git .*review-rev[0-9]" "$P/changes-test2.diff" "no *-review-rev* review artifacts included"
assert_file_grep "^diff --git a/newfile\.txt" "$P/changes-test2.diff" "non-artifact untracked files still included"

group "commits mode"

run "$SKILL_DIR/scripts/compute-diff.sh" --mode commits --start HEAD~1 --end HEAD --out "$P/changes-range.diff"
assert_rc 0 "commit range diff exits 0"
assert_file_grep "^-hello v1" "$P/changes-range.diff" "range diff shows the committed old content"
assert_file_grep "^\+hello v2" "$P/changes-range.diff" "range diff shows the committed new content"
assert_file_not_grep "hello v3" "$P/changes-range.diff" "range diff ignores the working tree"

run "$SKILL_DIR/scripts/compute-diff.sh" --mode commits --start HEAD --end HEAD --out "$P/changes-empty.diff"
assert_rc_nonzero "empty commit range fails"
assert_grep "no changes to review" "empty commit range error message"
assert_missing "$P/changes-empty.diff" "empty diff file is removed"

run "$SKILL_DIR/scripts/compute-diff.sh" --mode commits --start nosuchref --end HEAD --out "$P/changes-bad.diff"
assert_rc_nonzero "unknown commit ref fails"
assert_grep "start commit not found: nosuchref" "unknown commit ref error message"

run "$SKILL_DIR/scripts/compute-diff.sh" --mode commits --out "$P/changes-nostart.diff"
assert_rc 1 "commits mode without start/end fails"
assert_grep "--start and --end are required" "commits mode without start/end error message"

group "guards and usage"

run "$SKILL_DIR/scripts/compute-diff.sh"
assert_rc 2 "no arguments fails"
assert_grep "Usage: compute-diff\.sh" "no arguments prints usage"

run "$SKILL_DIR/scripts/compute-diff.sh" --help
assert_rc 0 "--help exits 0"
assert_grep "Usage: compute-diff\.sh" "--help prints usage"

run "$SKILL_DIR/scripts/compute-diff.sh" --mode bogus --out "$P/changes-x.diff"
assert_rc 1 "unknown mode fails"
assert_grep "unknown mode: bogus" "unknown mode error message"

mkdir -p "$WORK_DIR/notrepo"
(
    cd "$WORK_DIR/notrepo" || exit 1
    GIT_CEILING_DIRECTORIES="$WORK_DIR" "$SKILL_DIR/scripts/compute-diff.sh" \
        --mode uncommitted --out "$WORK_DIR/notrepo/x.diff"
) >"$OUT_FILE" 2>&1
RC=$?
assert_rc_nonzero "outside a git repository fails"
assert_grep "not inside a git work tree" "outside a git repository error message"

echo
echo "Test workspace (kept for inspection): $WORK_DIR"
finish
