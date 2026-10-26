#!/usr/bin/env bash
# Orchestrate a review of PDD artifacts with the ponytail-review-readonly
# opencode agent (non-interactive session).
#
# What it does:
#   1. Validates the parameters and the PDD artifacts.
#   2. For code reviews, computes the diff into {project_dir}/changes-{UUID}.diff
#      (via compute-diff.sh).
#   3. Picks the next review revision {J}: the first rev{J} file that does not
#      exist yet (rev1, rev2, ...).
#   4. Detects the codebase summary index at {project_dir}/../../summary/index.md.
#   5. Builds the review prompt and runs:
#        opencode run --agent ponytail-review-readonly --model MODEL#EFFORT PROMPT
#
# Usage:
#   run-review.sh --project-dir DIR --subject SUBJECT [options]
#
# Options:
#   --step N               implementation plan step number (required for
#                          code-uncommitted and code-commits)
#   --start-commit REF     first commit of the range (required for code-commits)
#   --end-commit REF       last commit of the range (default: HEAD; code-commits only)
#   --model MODEL          opencode model (default: edenai/zai/glm-5.3)
#   --reasoning-effort E   reasoning-effort variant appended as #E; default: max;
#                          pass an empty value to use the model without a variant
#   --dry-run              validate, show resolved paths and the prompt; do not
#                          compute the diff and do not launch opencode
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_ID="ponytail-review-readonly"
DEFAULT_MODEL="edenai/zai/glm-5.3"
DEFAULT_REASONING_EFFORT="max"

usage() {
    cat >&2 <<EOF
Usage: run-review.sh --project-dir DIR --subject SUBJECT [options]

Required:
  --project-dir DIR     PDD project directory (contains rough-idea.md,
                        idea-honing.md, research/, design/, implementation/)
  --subject SUBJECT     tech-design | code-uncommitted | code-commits |
                        final-pdd-review

Options:
  --step N              implementation plan step number (required for
                        code-uncommitted and code-commits; invalid otherwise)
  --start-commit REF    first commit of the range (required for code-commits)
  --end-commit REF      last commit of the range (default: HEAD; code-commits
                        only)
  --model MODEL         opencode model (default: $DEFAULT_MODEL)
  --reasoning-effort E  reasoning-effort variant appended as #E (default:
                        $DEFAULT_REASONING_EFFORT; empty value = no variant)
  --dry-run             validate and show the plan and prompt; no side effects
  -h, --help            show this help
EOF
}

die() { echo "Error: $*" >&2; exit 1; }
warn() { echo "Warning: $*" >&2; }

PROJECT_DIR=""
SUBJECT=""
STEP=""
START_COMMIT=""
END_COMMIT=""
END_GIVEN="false"
MODEL="$DEFAULT_MODEL"
REASONING_EFFORT="$DEFAULT_REASONING_EFFORT"
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-dir)      PROJECT_DIR="${2:-}"; shift 2 ;;
        --subject)          SUBJECT="${2:-}"; shift 2 ;;
        --step)             STEP="${2:-}"; shift 2 ;;
        --start-commit)     START_COMMIT="${2:-}"; shift 2 ;;
        --end-commit)       END_COMMIT="${2:-}"; END_GIVEN="true"; shift 2 ;;
        --model)            MODEL="${2:-}"; shift 2 ;;
        --reasoning-effort) REASONING_EFFORT="${2:-}"; shift 2 ;;
        --dry-run)          DRY_RUN="true"; shift ;;
        -h|--help)          usage; exit 0 ;;
        *) die "unknown argument: $1 (see --help)" ;;
    esac
done

# ---------------------------------------------------------------- validation

[[ -n "$PROJECT_DIR" ]] || die "--project-dir is required (see --help)"
[[ -n "$SUBJECT" ]] || die "--subject is required (see --help)"

case "$SUBJECT" in
    tech-design|code-uncommitted|code-commits|final-pdd-review) ;;
    *) die "invalid --subject '$SUBJECT': expected tech-design, code-uncommitted, code-commits or final-pdd-review" ;;
esac

case "$SUBJECT" in
    tech-design|final-pdd-review)
        [[ -z "$STEP" ]] || die "--step does not apply to --subject $SUBJECT"
        [[ -z "$START_COMMIT" && "$END_GIVEN" == "false" ]] \
            || die "--start-commit/--end-commit only apply to --subject code-commits"
        ;;
    code-uncommitted)
        [[ -n "$STEP" ]] || die "--step is required for --subject code-uncommitted"
        [[ -z "$START_COMMIT" && "$END_GIVEN" == "false" ]] \
            || die "--start-commit/--end-commit only apply to --subject code-commits"
        ;;
    code-commits)
        [[ -n "$STEP" ]] || die "--step is required for --subject code-commits"
        [[ -n "$START_COMMIT" ]] || die "--start-commit is required for --subject code-commits"
        END_COMMIT="${END_COMMIT:-HEAD}"
        ;;
esac

if [[ "$SUBJECT" == code-* && -n "$STEP" ]]; then
    [[ "$STEP" =~ ^[0-9]+$ && "$STEP" -gt 0 ]] \
        || die "--step must be a positive integer, got '$STEP'"
fi

[[ -d "$PROJECT_DIR" ]] || die "project directory not found: $PROJECT_DIR"
PROJECT_ABS="$(cd "$PROJECT_DIR" && pwd)"

for cmd in git opencode; do
    command -v "$cmd" >/dev/null 2>&1 \
        || die "$cmd is required but not installed. Install it and retry."
done

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" \
    || die "not inside a git repository: $(pwd)"
# All git output and paths given to the reviewer must be relative to the
# repository root (the reviewer session runs there).
cd "$GIT_ROOT"

DESIGN="$PROJECT_ABS/design/detailed-design.md"
PLAN="$PROJECT_ABS/implementation/plan.md"
ROUGH_IDEA="$PROJECT_ABS/rough-idea.md"
HONING="$PROJECT_ABS/idea-honing.md"
RESEARCH_DIR="$PROJECT_ABS/research"

case "$SUBJECT" in
    tech-design)
        [[ -f "$DESIGN" ]] || die "technical design not found: $DESIGN"
        ;;
    code-*)
        [[ -f "$PLAN" ]] || die "implementation plan not found: $PLAN"
        if ! grep -q "Step ${STEP}:" "$PLAN"; then
            die "implementation plan step not found: no 'Step ${STEP}:' heading in $PLAN"
        fi
        ;;
    final-pdd-review)
        [[ -f "$DESIGN" ]] || die "technical design not found: $DESIGN"
        [[ -f "$PLAN" ]] || die "implementation plan not found: $PLAN"
        ;;
esac

if [[ ! -f "$ROUGH_IDEA" ]]; then warn "rough idea not found: $ROUGH_IDEA"; fi
if [[ ! -f "$HONING" ]]; then warn "requirements file not found: $HONING"; fi

# ------------------------------------------------- opencode agent discovery

PROJECT_AGENT_FILE="$GIT_ROOT/.opencode/agents/${AGENT_ID}.md"
GLOBAL_AGENT_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/agents/${AGENT_ID}.md"

if [[ -f "$PROJECT_AGENT_FILE" ]]; then
    AGENT_SOURCE="project"
elif [[ -f "$GLOBAL_AGENT_FILE" ]]; then
    AGENT_SOURCE="global"
    warn "using the globally installed agent $GLOBAL_AGENT_FILE; its read-only permissions were not verified"
else
    cat >&2 <<EOF
Error: the opencode agent '$AGENT_ID' is not installed in this project.
Install it by copying the epinoia repository's .opencode/ directory into $GIT_ROOT:
  .opencode/agents/${AGENT_ID}.md   (the agent)
  .opencode/opencode.json            (its read-only permissions)
EOF
    exit 1
fi

if [[ "$AGENT_SOURCE" == "project" ]]; then
    CONFIG_HAS_AGENT="false"
    for cfg in "$GIT_ROOT/.opencode/opencode.json" "$GIT_ROOT/.opencode/opencode.jsonc" \
               "$GIT_ROOT/opencode.json" "$GIT_ROOT/opencode.jsonc"; do
        if [[ -f "$cfg" ]] && grep -q '"ponytail-review-readonly"' "$cfg"; then
            CONFIG_HAS_AGENT="true"
            break
        fi
    done
    if [[ "$CONFIG_HAS_AGENT" != "true" ]] && ! grep -q '^permissions:' "$PROJECT_AGENT_FILE"; then
        cat >&2 <<EOF
Error: the agent '$AGENT_ID' has no read-only permissions configured.
Copy the epinoia repository's .opencode/opencode.json to $GIT_ROOT/.opencode/opencode.json
(it defines agents."$AGENT_ID".permissions), or add a permissions block to the
agent's Markdown frontmatter yourself.
EOF
        exit 1
    fi
fi

# ------------------------------------------------------------ review target

DIFF_FILE=""
if [[ "$SUBJECT" == code-* && "$DRY_RUN" != "true" ]]; then
    UUID=""
    if command -v uuidgen >/dev/null 2>&1; then
        UUID="$(uuidgen)"
    elif [[ -r /proc/sys/kernel/random/uuid ]]; then
        UUID="$(cat /proc/sys/kernel/random/uuid)"
    elif command -v python3 >/dev/null 2>&1; then
        UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
    else
        die "cannot generate a UUID (need uuidgen, /proc/sys/kernel/random/uuid or python3)"
    fi
    DIFF_FILE="$PROJECT_ABS/changes-$UUID.diff"
    if [[ "$SUBJECT" == "code-uncommitted" ]]; then
        "$SCRIPT_DIR/compute-diff.sh" --mode uncommitted --out "$DIFF_FILE" >/dev/null
    else
        "$SCRIPT_DIR/compute-diff.sh" --mode commits \
            --start "$START_COMMIT" --end "$END_COMMIT" --out "$DIFF_FILE" >/dev/null
    fi
elif [[ "$SUBJECT" == code-* ]]; then
    DIFF_FILE="<computed on the real run: {project_dir}/changes-<uuid>.diff>"
fi

case "$SUBJECT" in
    tech-design)       REVIEW_BASE="$PROJECT_ABS/design/detailed-design-review-rev" ;;
    code-*)            REVIEW_BASE="$PROJECT_ABS/implementation/step-${STEP}-review-rev" ;;
    final-pdd-review)  REVIEW_BASE="$PROJECT_ABS/summary-review-rev" ;;
esac
J=1
while [[ -e "${REVIEW_BASE}${J}.md" ]]; do
    J=$((J + 1))
done
REVIEW_FILE="${REVIEW_BASE}${J}.md"

# Codebase summary written by the codebase-summary skill (a sibling of the
# planning directory that contains the PDD project).
SUMMARY_INDEX=""
if [[ -f "$PROJECT_ABS/../../summary/index.md" ]]; then
    SUMMARY_INDEX="$PROJECT_ABS/../../summary/index.md"
fi

# ------------------------------------------------------------- model choice

if [[ -n "$REASONING_EFFORT" ]]; then
    MODEL_SELECTOR="${MODEL}#${REASONING_EFFORT}"
else
    MODEL_SELECTOR="$MODEL"
fi

# ---------------------------------------------------------- relative paths

# Paths given to opencode must be relative to the repository root (the
# session's working directory); fall back to absolute when the path is
# outside the repository.
rel() {
    local p="$1" rel_path=""
    if command -v realpath >/dev/null 2>&1; then
        rel_path="$(realpath --relative-to="$GIT_ROOT" "$p" 2>/dev/null || true)"
    elif command -v python3 >/dev/null 2>&1; then
        rel_path="$(python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$p" "$GIT_ROOT" 2>/dev/null || true)"
    fi
    if [[ -n "$rel_path" && "$rel_path" != ..* ]]; then
        printf '%s' "$rel_path"
    else
        printf '%s' "$p"
    fi
}

REL_PROJECT="$(rel "$PROJECT_ABS")"
REL_DESIGN="$(rel "$DESIGN")"
REL_PLAN="$(rel "$PLAN")"
REL_ROUGH_IDEA="$(rel "$ROUGH_IDEA")"
REL_HONING="$(rel "$HONING")"
REL_REVIEW="$(rel "$REVIEW_FILE")"
REL_DIFF="$DIFF_FILE"
if [[ -n "$DIFF_FILE" && "$DRY_RUN" != "true" ]]; then
    REL_DIFF="$(rel "$DIFF_FILE")"
fi
REL_SUMMARY=""
if [[ -n "$SUMMARY_INDEX" ]]; then
    REL_SUMMARY="$(rel "$SUMMARY_INDEX")"
fi

# ------------------------------------------------------------------ prompt

EXTRA=""
if [[ -d "$RESEARCH_DIR" && "$SUBJECT" == "tech-design" ]]; then
    EXTRA="Research notes are under $REL_PROJECT/research."
fi
if [[ -n "$REL_SUMMARY" ]]; then
    if [[ -n "$EXTRA" ]]; then EXTRA="$EXTRA "; fi
    EXTRA="${EXTRA}For an overview of the codebase, first read $REL_SUMMARY."
fi

if [[ "$SUBJECT" == "tech-design" ]]; then
    TASK="Review the technical design located at $REL_DESIGN."
    CONTEXT="Judge the design against the rough idea ($REL_ROUGH_IDEA), the requirements refined in $REL_HONING, and the research behind it."
elif [[ "$SUBJECT" == code-* ]]; then
    TASK="Review the code $REL_DIFF corresponding to implementation step $STEP."
    CONTEXT="Judge the code against the technical design ($REL_DESIGN) and the implementation plan ($REL_PLAN), taking into account implementation step $STEP: read the \"Step $STEP:\" section of the plan before reviewing."
else
    TASK="Review if this codebase is a sound and complete implementation of the requirements and tech design specified in $REL_PROJECT."
    CONTEXT="Judge the implementation against the rough idea ($REL_ROUGH_IDEA), the requirements refined in $REL_HONING, the technical design ($REL_DESIGN), and the implementation plan ($REL_PLAN); every step of the plan should be implemented and demoable."
fi

PROMPT="$TASK

Write your review to $REL_REVIEW.

Context:
- PDD project directory: $REL_PROJECT. $CONTEXT $EXTRA
- All paths are relative to the repository root. The review file does not exist yet; create it with your report."

# ------------------------------------------------------------------- output

if [[ "$DRY_RUN" == "true" ]]; then
    echo "Subject:        $SUBJECT"
    echo "Project dir:    $PROJECT_ABS"
    if [[ -n "$STEP" ]]; then echo "Step:           $STEP"; fi
    if [[ "$SUBJECT" == "code-commits" ]]; then echo "Commit range:   $START_COMMIT..$END_COMMIT"; fi
    if [[ "$SUBJECT" == code-* ]]; then echo "Diff file:      $DIFF_FILE"; fi
    echo "Review file:    $REVIEW_FILE"
    if [[ -n "$REL_SUMMARY" ]]; then
        echo "Summary index:  $REL_SUMMARY"
    else
        echo "Summary index:  none found"
    fi
    echo "Agent:          $AGENT_ID ($AGENT_SOURCE)"
    echo "Model selector: $MODEL_SELECTOR"
    echo
    echo "Prompt:"
    echo "-----"
    echo "$PROMPT"
    echo "-----"
    exit 0
fi

echo "Review file: $REVIEW_FILE" >&2
if [[ -n "$DIFF_FILE" ]]; then echo "Diff file:   $DIFF_FILE" >&2; fi
echo "Launching opencode ($MODEL_SELECTOR); this can take several minutes..." >&2

exec opencode run --agent "$AGENT_ID" --model "$MODEL_SELECTOR" "$PROMPT"
