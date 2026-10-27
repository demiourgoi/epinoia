#!/usr/bin/env bash
# Shared assertion helpers for all test suites in tests/. Source this file
# from a suite (usually via a per-skill lib.sh); it is not a test on its own.
#
# A suite runs any number of checks with the assert_* helpers and ends with
# finish, which prints a summary and returns non-zero when anything failed.

TESTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$TESTS_ROOT/.." && pwd)"
# Shared workspace inside the repository's gitignored .local/; suites may
# override it with their own subdirectory.
WORK_DIR="$REPO_ROOT/.local/tests"

TESTS_RUN=0
TESTS_FAILED=0
OUT_FILE="$(mktemp)"
RC=0
trap 'rm -f "$OUT_FILE"' EXIT

ok() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "  PASS $1"
}

fail() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "  FAIL $1"
}

group() {
    echo
    echo "== $1 =="
}

# run <cmd...>          capture stdout+stderr of a command into $OUT_FILE
# run_in <dir> <cmd...>  same, but with the command's cwd in <dir>
run() {
    "$@" >"$OUT_FILE" 2>&1
    RC=$?
}

run_in() {
    local dir="$1"
    shift
    ( cd "$dir" && "$@" ) >"$OUT_FILE" 2>&1
    RC=$?
}

assert_rc() {
    local want="$1" desc="$2"
    if [[ "$RC" -eq "$want" ]]; then
        ok "$desc"
    else
        fail "$desc (rc=$RC, want $want)"
    fi
}

assert_rc_nonzero() {
    local desc="$1"
    if [[ "$RC" -ne 0 ]]; then
        ok "$desc"
    else
        fail "$desc (unexpected rc=0)"
    fi
}

# assert_grep / assert_not_grep work on the output of the last run() call;
# assert_file_grep works on an arbitrary file.
assert_grep() {
    local pattern="$1" desc="$2"
    if grep -qE -- "$pattern" "$OUT_FILE"; then
        ok "$desc"
    else
        fail "$desc"
    fi
}

assert_not_grep() {
    local pattern="$1" desc="$2"
    if grep -qE -- "$pattern" "$OUT_FILE"; then
        fail "$desc"
    else
        ok "$desc"
    fi
}

assert_file_grep() {
    local pattern="$1" f="$2" desc="$3"
    if grep -qE -- "$pattern" "$f" 2>/dev/null; then
        ok "$desc"
    else
        fail "$desc ($f)"
    fi
}

assert_file_not_grep() {
    local pattern="$1" f="$2" desc="$3"
    if grep -qE -- "$pattern" "$f" 2>/dev/null; then
        fail "$desc ($f)"
    else
        ok "$desc"
    fi
}

assert_exists() {
    local f="$1" desc="$2"
    if [[ -e "$f" ]]; then
        ok "$desc"
    else
        fail "$desc ($f)"
    fi
}

assert_missing() {
    local f="$1" desc="$2"
    if [[ ! -e "$f" ]]; then
        ok "$desc"
    else
        fail "$desc ($f)"
    fi
}

assert_nonempty() {
    local f="$1" desc="$2"
    if [[ -s "$f" ]]; then
        ok "$desc"
    else
        fail "$desc ($f)"
    fi
}

assert_glob_empty() {
    local pattern="$1" desc="$2" matches=""
    matches="$(compgen -G "$pattern" || true)"
    if [[ -z "$matches" ]]; then
        ok "$desc"
    else
        fail "$desc (matched: $matches)"
    fi
}

assert_glob_nonempty() {
    local pattern="$1" desc="$2" matches=""
    matches="$(compgen -G "$pattern" || true)"
    if [[ -n "$matches" ]]; then
        ok "$desc"
    else
        fail "$desc (no match for $pattern)"
    fi
}

finish() {
    echo
    echo "$(basename "$0"): $TESTS_RUN tests, $TESTS_FAILED failures"
    [[ "$TESTS_FAILED" -eq 0 ]]
}
