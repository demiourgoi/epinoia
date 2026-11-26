#!/usr/bin/env bash
# Hermetic tests for the repository Makefile's install target: skills go to
# TARGET_DIR/.agents/skills/, the opencode agent plus config go to the git root
# of TARGET_DIR (or to TARGET_DIR itself outside a git repository), the vibe
# agent plus config go to TARGET_DIR, and bad targets are rejected.
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
assert_exists "$PKG/.agents/skills/mistral-vibe-cli/SKILL.md" "installs the mistral-vibe-cli skill into the package"
assert_exists "$MONOREPO/.opencode/agents/ponytail-review-readonly.md" "installs the opencode agent at the git root"
assert_exists "$MONOREPO/.opencode/agents/LICENSE" "installs the agent license sidecar at the git root"
assert_exists "$MONOREPO/.opencode/opencode.json" "installs the opencode config at the git root"
assert_file_grep "ponytail-review-readonly" "$MONOREPO/.opencode/opencode.json" "installed config defines the agent permissions"
assert_exists "$PKG/.vibe/config.toml" "installs the vibe config into the package"
assert_exists "$PKG/.vibe/agents/ponytail-reviewer.toml" "installs the vibe agent into the package"
assert_missing "$PKG/.opencode/opencode.json" "does not install opencode files into the package"
assert_missing "$MONOREPO/.vibe/config.toml" "does not install vibe files at the git root"

group "install target: TARGET_DIR is the git root"

run make -C "$REPO_ROOT" install TARGET_DIR="$MONOREPO"
assert_rc 0 "install into the repository root exits 0"
assert_exists "$MONOREPO/.opencode/opencode.json" "installs the opencode config into the repository root"
assert_exists "$MONOREPO/.vibe/config.toml" "installs the vibe config into the repository root"
assert_exists "$MONOREPO/.agents/skills/ponytail-review-pdd/SKILL.md" "installs the skills into the repository root"
assert_exists "$MONOREPO/.agents/skills/mistral-vibe-cli/SKILL.md" "installs the mistral-vibe-cli skill into the repository root"

group "install target: default TARGET_DIR is the caller's PWD"

# PWD outside any git repository: the opencode files fall back to TARGET_DIR.
DEFAULT_DIR="$(mktemp -d /tmp/ponytail-install-default.XXXXXX)"
run env PWD="$DEFAULT_DIR" make -C "$REPO_ROOT" install
assert_rc 0 "install without explicit TARGET_DIR exits 0"
assert_exists "$DEFAULT_DIR/.agents/skills/ponytail-review-pdd/SKILL.md" "default install uses the caller's PWD for skills"
assert_exists "$DEFAULT_DIR/.opencode/opencode.json" "default install falls back to TARGET_DIR outside a repository"
assert_exists "$DEFAULT_DIR/.vibe/config.toml" "default install puts the vibe config in TARGET_DIR outside a repository"
rm -rf "$DEFAULT_DIR"

group "install target: reinstall"

run make -C "$REPO_ROOT" install TARGET_DIR="$PKG"
assert_rc 0 "reinstall exits 0"
assert_exists "$MONOREPO/.opencode/opencode.json" "reinstall keeps the config in place"
assert_exists "$PKG/.vibe/config.toml" "reinstall keeps the vibe config in place"

group "install target: every listed skill installs"

# The SKILLS list in the Makefile is the contract: each of its entries must
# land as a SKILL.md in the target. SKILLS_LIST mirrors the Makefile's list
# and is compared against it below, so the two cannot drift apart silently.
SKILLS_LIST="codebase-summary edenai-zed-config mistral-vibe-cli pdd ponytail-review ponytail-review-pdd"

for SKILL in $SKILLS_LIST; do
    assert_exists "$PKG/.agents/skills/$SKILL/SKILL.md" "installs the listed skill $SKILL"
done

group "install target: skill registry completeness"

# The Makefile installs only the skills SKILLS lists, so an unlisted skills/
# directory would be silently dropped. Assert both directions: every
# directory in skills/ appears in the Makefile's SKILLS variable, and this
# suite's SKILLS_LIST matches it exactly.
SKILLS_MAKE="$(awk '
    /^SKILLS :=/ { collect = 1; sub(/^SKILLS :=[ \t]*/, ""); acc = $0; next }
    collect && /^[ \t]/ { acc = acc " " $0; next }
    collect { collect = 0 }
    END { gsub(/\\/, "", acc); print acc }
' "$REPO_ROOT/Makefile" | tr -s "[:space:]" " " | sed "s/^ //; s/ $//")"

# assert_nonempty takes a file path, so the parsed variable is checked directly.
if [ -n "$SKILLS_MAKE" ]; then
    ok "the Makefile defines a SKILLS variable"
else
    fail "the Makefile defines a SKILLS variable"
fi
if [ "$SKILLS_MAKE" = "$SKILLS_LIST" ]; then
    ok "the suite's skill list matches the Makefile's SKILLS"
else
    fail "the suite's skill list matches the Makefile's SKILLS (suite: $SKILLS_LIST; makefile: $SKILLS_MAKE)"
fi

for SKILL_DIR in "$REPO_ROOT"/skills/*/; do
    SKILL_NAME="$(basename "$SKILL_DIR")"
    case " $SKILLS_MAKE " in
        *" $SKILL_NAME "*) ok "the skills/ directory $SKILL_NAME is listed in SKILLS" ;;
        *) fail "the skills/ directory $SKILL_NAME is listed in SKILLS" ;;
    esac
done

group "install target: skill registry guard"

# A listed skill missing from skills/ must fail the install loudly. The
# install target refuses to read from a repository it is installing into, so
# the guard runs against a throwaway copy of this repository with one listed
# skill directory removed.
REPO_COPY="$WORK_DIR/install-repo-copy"
mkdir -p "$REPO_COPY"
tar -C "$REPO_ROOT" --exclude=.git --exclude=.local -cf - . | tar -C "$REPO_COPY" -xf -
rm -rf "$REPO_COPY/skills/ponytail-review-pdd"
GUARD_TARGET="$WORK_DIR/install-guard-target"
mkdir -p "$GUARD_TARGET"
run make -C "$REPO_COPY" install TARGET_DIR="$GUARD_TARGET"
assert_rc 2 "install with a listed skill missing exits 2"
assert_grep "listed skill directory not found: skills/ponytail-review-pdd" "missing-skill error message"
assert_missing "$GUARD_TARGET/.vibe/config.toml" "does not install other artifacts when a skill is missing"
rm -rf "$REPO_COPY" "$GUARD_TARGET"

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
