#!/usr/bin/env bash
# Fixture and helpers for the ponytail-review-pdd test suites. Sources the
# shared assertion helpers from ../../lib.sh and provides setup_repo.

. "$(dirname "${BASH_SOURCE[0]}")/../../lib.sh"

SKILL_DIR="$REPO_ROOT/skills/ponytail-review-pdd"

# Every suite rebuilds the same workspace, which is kept afterwards so
# failures can be inspected. The workspace lives inside the repository's
# gitignored .local/ (not in /tmp) so the live e2e opencode sessions run
# inside a context the developer's opencode credentials can reach.
WORK_DIR="$REPO_ROOT/.local/ponytail-review-pdd-tests"
TEST_REPO="$WORK_DIR/repo"
P="$TEST_REPO/.agents/planning/2026-10-26-demo"

# Creates a fresh test repository with a PDD project and the opencode agent
# installed the way a target project would have it, and leaves the working
# directory inside the test repository.
#
# State after setup:
#   - two commits (base.txt = "hello v2" at HEAD, "hello v1" at HEAD~1)
#   - uncommitted work: base.txt modified, stagedfile.txt staged (new),
#     newfile.txt untracked, and the untracked opencode agent installation
#     files (.opencode/agents/*, .opencode/opencode.json)
setup_repo() {
    rm -rf "$TEST_REPO"
    mkdir -p "$P/research" "$P/design" "$P/implementation" \
        "$TEST_REPO/.agents/summary" "$TEST_REPO/.opencode/agents" \
        "$TEST_REPO/sub/dir"
    printf 'Rough idea\ntemplate manager\n' > "$P/rough-idea.md"
    printf 'Q1? A1\n'                    > "$P/idea-honing.md"
    printf 'research notes\n'            > "$P/research/technologies.md"
    printf '# Design\nTest design doc\n' > "$P/design/detailed-design.md"
    {
        printf '# Plan\n'
        printf '## Step 1: skeleton\nObjective\n'
        printf '## Step 2: api\nObjective\n'
    } > "$P/implementation/plan.md"
    printf 'codebase summary index\n' > "$TEST_REPO/.agents/summary/index.md"
    printf 'hello v1\n' > "$TEST_REPO/base.txt"

    git -C "$TEST_REPO" init -q
    git -C "$TEST_REPO" config user.email tests@local
    git -C "$TEST_REPO" config user.name tests
    git -C "$TEST_REPO" add -A
    git -C "$TEST_REPO" commit -qm initial
    printf 'hello v2\n' > "$TEST_REPO/base.txt"
    git -C "$TEST_REPO" commit -qam second

    printf 'hello v3 uncommitted\n' > "$TEST_REPO/base.txt"
    printf 'staged content\n'        > "$TEST_REPO/stagedfile.txt"
    printf 'new untracked\n'         > "$TEST_REPO/newfile.txt"
    git -C "$TEST_REPO" add stagedfile.txt

    cp "$REPO_ROOT/.opencode/agents/ponytail-review-readonly.md" \
       "$TEST_REPO/.opencode/agents/ponytail-review-readonly.md"
    cp "$REPO_ROOT/.opencode/opencode.json" "$TEST_REPO/.opencode/opencode.json"

    cd "$TEST_REPO"
}
