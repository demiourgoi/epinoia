#!/usr/bin/env bash
# Hermetic tests for the repository Makefile's install target: it must copy
# the skills into TARGET_DIR/.agents/skills/ and the opencode agent plus
# config into TARGET_DIR/.opencode/, default TARGET_DIR to the caller's PWD,
# and reject bad targets.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

INSTALL_DIR="$WORK_DIR/install-target"
DEFAULT_DIR="$WORK_DIR/install-default"

group "install target"

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

run make -C "$REPO_ROOT" install TARGET_DIR="$INSTALL_DIR"
assert_rc 0 "make install exits 0"
assert_exists "$INSTALL_DIR/.agents/skills/ponytail-review-pdd/SKILL.md" "installs the ponytail-review-pdd skill"
assert_exists "$INSTALL_DIR/.agents/skills/ponytail-review-pdd/scripts/run-review.sh" "installs the skill scripts"
assert_exists "$INSTALL_DIR/.agents/skills/pdd/SKILL.md" "installs the other skills"
assert_exists "$INSTALL_DIR/.opencode/agents/ponytail-review-readonly.md" "installs the opencode agent"
assert_exists "$INSTALL_DIR/.opencode/agents/LICENSE" "installs the agent license sidecar"
assert_exists "$INSTALL_DIR/.opencode/opencode.json" "installs the opencode config"
assert_file_grep "ponytail-review-readonly" "$INSTALL_DIR/.opencode/opencode.json" "installed config defines the agent permissions"

group "install target: default TARGET_DIR is the caller's PWD"

rm -rf "$DEFAULT_DIR"
mkdir -p "$DEFAULT_DIR"
# Simulates: cd <project> && make -C <this repo> install
# PWD is inherited from the caller's shell; make -C does not rewrite it.
run env PWD="$DEFAULT_DIR" make -C "$REPO_ROOT" install
assert_rc 0 "install without explicit TARGET_DIR exits 0"
assert_exists "$DEFAULT_DIR/.agents/skills/ponytail-review-pdd/SKILL.md" "default install uses the caller's PWD for skills"
assert_exists "$DEFAULT_DIR/.opencode/opencode.json" "default install uses the caller's PWD for opencode"

group "install target: reinstall"

run make -C "$REPO_ROOT" install TARGET_DIR="$INSTALL_DIR"
assert_rc 0 "reinstall exits 0"
assert_exists "$INSTALL_DIR/.opencode/opencode.json" "reinstall keeps the config in place"

group "install target: guards"

run env PWD= make -C "$REPO_ROOT" install
assert_rc 2 "install without a determinable TARGET_DIR exits 2"
assert_grep "could not determine TARGET_DIR" "missing TARGET_DIR error message"

run make -C "$REPO_ROOT" install TARGET_DIR="$INSTALL_DIR/does-not-exist"
assert_rc 2 "install into a missing directory exits 2"
assert_grep "target directory does not exist" "missing directory error message"

run make -C "$REPO_ROOT" install TARGET_DIR="$REPO_ROOT"
assert_rc 2 "install into the repository itself exits 2"
assert_grep "TARGET_DIR is this repository" "self-install error message (explicit TARGET_DIR)"

run env PWD="$REPO_ROOT" make -C "$REPO_ROOT" install
assert_rc 2 "defaulting TARGET_DIR to the repository itself exits 2"
assert_grep "TARGET_DIR is this repository" "self-install error message (defaulted TARGET_DIR)"

echo
echo "Test workspace (kept for inspection): $WORK_DIR"
finish
