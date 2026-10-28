#!/usr/bin/env bash
# Runs every test suite in this codebase's tests/ tree.
#
# A suite is any test-*.sh file under tests/ (for example
# tests/skills/<skill>/test-*.sh). Suites whose basename starts with
# test-e2e are live end-to-end tests: they need network access and opencode
# authentication, and they spend model tokens, so they only run when asked
# for explicitly.
#
# Usage:
#   tests/run.sh              all hermetic suites
#   tests/run.sh --e2e        hermetic suites plus live end-to-end suites
#   tests/run.sh --e2e-only   only the live end-to-end suites
#
# End-to-end model overrides (see the e2e suites):
#   E2E_MODEL                (default: mistral/zai-glm-5-3-flash)
#   E2E_REASONING_EFFORT     (default: empty, no variant)
set -u

TESTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat >&2 <<'EOF'
Usage: tests/run.sh [--e2e | --e2e-only]
  (default)    all hermetic suites (no network, no model calls)
  --e2e        also run the live end-to-end suites (spends model tokens)
  --e2e-only   only run the live end-to-end suites
EOF
}

E2E=false
E2E_ONLY=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --e2e)      E2E=true ;;
        --e2e-only) E2E_ONLY=true ;;
        -h|--help)  usage; exit 0 ;;
        *)          echo "Error: unknown option: $1" >&2; usage; exit 2 ;;
    esac
    shift
done

mapfile -t ALL_SUITES < <(find "$TESTS_ROOT" -type f -name 'test-*.sh' | sort)
if [[ ${#ALL_SUITES[@]} -eq 0 ]]; then
    echo "Error: no test suites found under $TESTS_ROOT" >&2
    exit 1
fi

suites=()
skipped=()
for suite in "${ALL_SUITES[@]}"; do
    case "$(basename "$suite")" in
        test-e2e*)
            if [[ "$E2E" == "true" || "$E2E_ONLY" == "true" ]]; then
                suites+=("$suite")
            else
                skipped+=("$suite")
            fi
            ;;
        *)
            if [[ "$E2E_ONLY" != "true" ]]; then
                suites+=("$suite")
            fi
            ;;
    esac
done

FAILED_SUITES=0
run_suite() {
    local suite="$1"
    echo
    echo "############ $suite ############"
    if bash "$suite"; then
        echo "############ $suite: OK ############"
    else
        FAILED_SUITES=$((FAILED_SUITES + 1))
        echo "############ $suite: FAILED ############"
    fi
}

for suite in "${suites[@]}"; do
    run_suite "$suite"
done

if [[ ${#skipped[@]} -gt 0 ]]; then
    echo
    echo "Skipped (needs --e2e):"
    for suite in "${skipped[@]}"; do
        echo "  $suite"
    done
fi

echo
if [[ "$FAILED_SUITES" -eq 0 ]]; then
    echo "ALL ${#suites[@]} SUITE(S) PASSED"
    exit 0
else
    echo "$FAILED_SUITES of ${#suites[@]} suite(s) FAILED"
    exit 1
fi
