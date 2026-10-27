#!/usr/bin/env bash
# Hermetic tests for the repository Makefile's install target: skills go to
# TARGET_DIR/.agents/skills/, the opencode agent plus config go to the git
# root of TARGET_DIR (or to TARGET_DIR itself outside a git repository), and
# bad targets are rejected.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

# A monorepo fixture for the git-root placement: PKG is a subdirectory of its
# own repository, like a package inside a monorepo.
MONOREPO="$WORK_DIR/install-monorepo"
PKG="$MONOREPO/pkg"

group "install target: package inside a git repository"

rm -rf "$MONOREPO"
mkdir -p "$PKG"
git -C "$MONOREPO" init -q

run make -C "$REPO_ROOT" install TARGET_DIR="$PKG"
assert_rc 0 "make install exits 0"
assert_exists "$PKG/.agents/skills/ponytail-review-pdd/SKILL.md" "installs the ponytail-review-pdd skill into the package"
assert_exists "$PKG/.agents/skills/ponytail-review-pdd/scripts/run-review.sh" "installs the skill scripts"
assert_exists "$PKG/.agents/skills/pdd/SKILL.md" "installs the other skills"
assert_exists "$MONOREPO/.opencode/agents/ponytail-review-readonly.md" "installs the opencode agent at the git root"
assert_exists "$MONOREPO/.opencode/agents/LICENSE" "installs the agent license sidecar at the git root"
assert_exists "$MONOREPO/.opencode/opencode.json" "installs the opencode config at the git root"
assert_file_grep "ponytail-review-readonly" "$MONOREPO/.opencode/opencode.json" "installed config defines the agent permissions"
assert_missing "$PKG/.opencode/opencode.json" "does not install opencode files into the package"

group "install target: TARGET_DIR is the git root"

run make -C "$REPO_ROOT" install TARGET_DIR="$MONOREPO"
assert_rc 0 "install into the repository root exits 0"
assert_exists "$MONOREPO/.opencode/opencode.json" "installs the opencode config into the repository root"
assert_exists "$MONOREPO/.agents/skills/ponytail-review-pdd/SKILL.md" "installs the skills into the repository root"

group "install target: default TARGET_DIR is the caller's PWD"

# PWD outside any git repository: the opencode files fall back to TARGET_DIR.
DEFAULT_DIR="$(mktemp -d /tmp/ponytail-install-default.XXXXXX)"
run env PWD="$DEFAULT_DIR" make -C "$REPO_ROOT" install
assert_rc 0 "install without explicit TARGET_DIR exits 0"
assert_exists "$DEFAULT_DIR/.agents/skills/ponytail-review-pdd/SKILL.md" "default install uses the caller's PWD for skills"
assert_exists "$DEFAULT_DIR/.opencode/opencode.json" "default install falls back to TARGET_DIR outside a repository"
rm -rf "$DEFAULT_DIR"

group "install target: reinstall"

run make -C "$REPO_ROOT" install TARGET_DIR="$PKG"
assert_rc 0 "reinstall exits 0"
assert_exists "$MONOREPO/.opencode/opencode.json" "reinstall keeps the config in place"

group "install target: guards"

run env PWD= make -C "$REPO_ROOT" install
assert_rc 2 "install without a determinable TARGET_DIR exits 2"
assert_grep "could not determine TARGET_DIR" "missing TARGET_DIR error message"

run make -C "$REPO_ROOT" install TARGET_DIR="$PKG/does-not-exist"
assert_rc 2 "install into a missing directory exits 2"
assert_grep "target directory does not exist" "missing directory error message"

run make -C "$REPO_ROOT" install TARGET_DIR="$REPO_ROOT"
assert_rc 2 "install into the repository itself exits 2"
assert_grep "TARGET_DIR is this repository" "self-install error message (explicit TARGET_DIR)"

run env PWD="$REPO_ROOT" make -C "$REPO_ROOT" install
assert_rc 2 "defaulting TARGET_DIR to the repository itself exits 2"
assert_grep "TARGET_DIR is this repository" "self-install error message (defaulted TARGET_DIR)"

# A directory inside this repository but not in its own git repo resolves to
# this repository's git root too, and must be refused.
PLAIN="$WORK_DIR/install-plain"
mkdir -p "$PLAIN"
run make -C "$REPO_ROOT" install TARGET_DIR="$PLAIN"
assert_rc 2 "install into a non-repository directory inside this repository exits 2"
assert_grep "TARGET_DIR is this repository" "self-install error message (git root inside this repository)"
rm -rf "$PLAIN"

echo
echo "Test workspace (kept for inspection): $WORK_DIR"
finish
