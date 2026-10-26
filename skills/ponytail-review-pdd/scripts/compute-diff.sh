#!/usr/bin/env bash
# Compute the git diff to review and save it to a file.
#
# Modes:
#   uncommitted  all uncommitted work: tracked changes (staged + unstaged)
#                against HEAD plus untracked files as new-file diffs
#   commits      the diff between two commits: git diff <start>..<end>
#
# Usage:
#   compute-diff.sh --mode uncommitted --out FILE
#   compute-diff.sh --mode commits --start REF --end REF --out FILE
#
# Review artifacts produced by this skill (changes-*.diff files and
# *-review-rev*.md review files) are excluded from uncommitted diffs, because
# they are review machinery, not work under review.
#
# Prints the diff file path on success. Exits non-zero on any problem.
set -euo pipefail

usage() {
    cat >&2 <<'EOF'
Usage: compute-diff.sh --mode uncommitted --out FILE
       compute-diff.sh --mode commits --start REF --end REF --out FILE
EOF
}

die() { echo "Error: $*" >&2; exit 1; }
warn() { echo "Warning: $*" >&2; }

MODE=""
OUT=""
START=""
END=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)  MODE="${2:-}";  shift 2 ;;
        --out)   OUT="${2:-}";   shift 2 ;;
        --start) START="${2:-}"; shift 2 ;;
        --end)   END="${2:-}";   shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown argument: $1" ;;
    esac
done

if [[ -z "$MODE" || -z "$OUT" ]]; then
    usage
    exit 2
fi

if ! command -v git >/dev/null 2>&1; then
    die "git is required but not installed. Install git and retry."
fi

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || die "not inside a git work tree: $(pwd)"

# Diff paths must be relative to the repository root (the reviewer session
# runs there), so run everything from the root. Resolve --out to an absolute
# path first, before changing directory.
case "$OUT" in
    /*) ;;
    *)  OUT="$(pwd)/$OUT" ;;
esac
cd "$(git rev-parse --show-toplevel)"

case "$MODE" in
    uncommitted)
        # Build in a temporary file outside the work tree and move it into
        # place at the end, so the diff file never lists itself as an
        # untracked file.
        TMP="$(mktemp)" || die "mktemp failed"
        if git rev-parse --verify HEAD >/dev/null 2>&1; then
            git --no-pager diff --no-color HEAD -- > "$TMP"
        else
            warn "no commits yet; only untracked files will be reviewed"
        fi
        # Untracked files (both untracked and unstaged work must be reviewed).
        while IFS= read -r f; do
            [[ -n "$f" ]] || continue
            case "$f" in
                changes-*.diff|*/changes-*.diff) continue ;;      # this skill's diffs
                *-review-rev*.md) continue ;;                     # this skill's reviews
            esac
            git --no-pager diff --no-color --no-index -- /dev/null "$f" >> "$TMP" || true
        done < <(git ls-files --others --exclude-standard)
        mv "$TMP" "$OUT"
        ;;
    commits)
        if [[ -z "$START" || -z "$END" ]]; then
            die "--start and --end are required when --mode is commits"
        fi
        if ! git rev-parse --verify --quiet "$START^{commit}" >/dev/null 2>&1; then
            die "start commit not found: $START"
        fi
        if ! git rev-parse --verify --quiet "$END^{commit}" >/dev/null 2>&1; then
            die "end commit not found: $END"
        fi
        git --no-pager diff --no-color "$START..$END" -- > "$OUT"
        ;;
    *)
        die "unknown mode: $MODE (expected uncommitted or commits)"
        ;;
esac

if [[ ! -s "$OUT" ]]; then
    rm -f "$OUT"
    die "no changes to review (the computed diff is empty)"
fi

echo "$OUT"
