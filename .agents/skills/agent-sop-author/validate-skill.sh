#!/bin/bash
set -euo pipefail

# Validate an agent skill created with the agent-sop-author skill.
#
# Checks:
# 1. Agent Skills format basics: SKILL.md present, YAML frontmatter with
#    required name/description fields, name matching the directory name
# 2. SOP prompt structure inside SKILL.md (Overview, Parameters,
#    Steps with numbered sub-steps and Constraints, RFC 2119 keywords)
# 3. Agent Skills specification compliance, authoritatively checked with
#    the skills-ref reference library (uvx --from skills-ref agentskills)
#
# Usage: validate-skill.sh <path-to-skill-directory>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <path-to-skill-directory>"
    exit 1
fi

SKILL_DIR="$1"
ERRORS=0
WARNINGS=0

if [ ! -d "$SKILL_DIR" ]; then
    echo "❌ Skill directory not found: $SKILL_DIR"
    exit 1
fi

SKILL_FILE="$SKILL_DIR/SKILL.md"

if [ ! -f "$SKILL_FILE" ]; then
    echo "❌ Missing required file: $SKILL_FILE"
    exit 1
fi

echo "Validating skill: $SKILL_DIR"
echo ""

# --- Agent Skills format: frontmatter ---

FRONTMATTER="$(awk 'NR==1 && $0 == "---" { fm = 1; next } fm == 1 && $0 == "---" { exit } fm == 1 { print }' "$SKILL_FILE")"

if [ "$(head -n 1 "$SKILL_FILE")" = "---" ]; then
    echo "✅ Frontmatter present"
else
    echo "❌ SKILL.md must start with a YAML frontmatter block delimited by ---"
    ERRORS=$((ERRORS+1))
fi

if printf '%s\n' "$FRONTMATTER" | grep -q '^description:'; then
    echo "✅ Frontmatter field present: description"
else
    echo "❌ Frontmatter missing required field: description"
    ERRORS=$((ERRORS+1))
fi

SKILL_NAME="$(printf '%s\n' "$FRONTMATTER" | grep '^name:' | head -n 1 | sed 's/^name:[[:space:]]*//' || true)"
DIR_NAME="$(basename "$SKILL_DIR")"

if [ -n "$SKILL_NAME" ]; then
    echo "✅ Frontmatter field present: name"
    if [[ ! "$SKILL_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
        echo "❌ name '$SKILL_NAME' must use lowercase letters, numbers and hyphens only, must not start or end with a hyphen and must not contain consecutive hyphens"
        ERRORS=$((ERRORS+1))
    fi
    if [ "${#SKILL_NAME}" -gt 64 ]; then
        echo "❌ name '$SKILL_NAME' exceeds 64 characters"
        ERRORS=$((ERRORS+1))
    fi
    if [ "$SKILL_NAME" != "$DIR_NAME" ]; then
        echo "❌ name '$SKILL_NAME' must match the skill directory name '$DIR_NAME'"
        ERRORS=$((ERRORS+1))
    fi
else
    echo "❌ Frontmatter missing required field: name"
    ERRORS=$((ERRORS+1))
fi

SKILL_DESCRIPTION="$(printf '%s\n' "$FRONTMATTER" | grep '^description:' | head -n 1 | sed 's/^description:[[:space:]]*//' || true)"
if [ -n "$SKILL_DESCRIPTION" ] && [ "${#SKILL_DESCRIPTION}" -gt 1024 ]; then
    echo "❌ description exceeds 1024 characters"
    ERRORS=$((ERRORS+1))
fi

# --- SOP prompt structure (body of SKILL.md) ---

check_section() {
    local section="$1"
    local pattern="$2"
    if grep -q "$pattern" "$SKILL_FILE"; then
        echo "✅ Section present: $section"
    else
        echo "❌ Missing required section: $section"
        ERRORS=$((ERRORS+1))
    fi
}

check_section "Title (H1)" "^# "
check_section "Overview" "^## Overview"
check_section "Parameters" "^## Parameters"
check_section "Steps" "^## Steps"

# Check Parameters section has constraints
if grep -q "^## Parameters" "$SKILL_FILE"; then
    if ! grep -A 20 "^## Parameters" "$SKILL_FILE" | grep -q "Constraints for parameter acquisition"; then
        echo "❌ Parameters section missing 'Constraints for parameter acquisition'"
        ERRORS=$((ERRORS+1))
    else
        echo "✅ Parameter constraints present"
    fi

    # Check for blank line after Parameters heading
    if ! grep -A 1 "^## Parameters$" "$SKILL_FILE" | tail -n 1 | grep -q "^$"; then
        echo "❌ Parameters section must have blank line after heading"
        ERRORS=$((ERRORS+1))
    else
        echo "✅ Blank line after Parameters heading"
    fi
fi

# Check for numbered steps
if ! grep -q "^### [0-9]\+\." "$SKILL_FILE"; then
    echo "❌ No numbered steps found (format: ### 1. Step Name)"
    ERRORS=$((ERRORS+1))
else
    echo "✅ Numbered steps present"
fi

# Check for Constraints sections in steps
if ! grep -q "^\*\*Constraints:\*\*" "$SKILL_FILE"; then
    echo "❌ No Constraints sections found in steps"
    ERRORS=$((ERRORS+1))
else
    echo "✅ Constraints sections present"
fi

# Check for RFC 2119 keywords
if ! grep -qE "You (MUST|SHOULD|MAY)" "$SKILL_FILE"; then
    echo "⚠️  No RFC 2119 keywords found (MUST, SHOULD, MAY)"
    WARNINGS=$((WARNINGS+1))
else
    echo "✅ RFC 2119 keywords present"
fi

# Check for negative constraints without context
if grep -E "You (MUST NOT|SHOULD NOT)" "$SKILL_FILE" | grep -v "because\|since\|as\|to avoid" > /dev/null 2>&1; then
    echo "⚠️  Negative constraints found without context (add 'because', 'since', etc.)"
    WARNINGS=$((WARNINGS+1))
fi

# Recommend Examples and Troubleshooting
if ! grep -q "^## Examples" "$SKILL_FILE"; then
    echo "⚠️  Recommended section missing: Examples"
    WARNINGS=$((WARNINGS+1))
fi

if ! grep -q "^## Troubleshooting" "$SKILL_FILE"; then
    echo "⚠️  Recommended section missing: Troubleshooting"
    WARNINGS=$((WARNINGS+1))
fi

# Recommend keeping SKILL.md under 500 lines (progressive disclosure)
SKILL_LINES="$(wc -l < "$SKILL_FILE")"
if [ "$SKILL_LINES" -gt 500 ]; then
    echo "⚠️  SKILL.md has $SKILL_LINES lines; keep it under 500 and move detail to references/"
    WARNINGS=$((WARNINGS+1))
fi

# --- Agent Skills specification validation (authoritative) ---

echo ""
echo "Running Agent Skills specification validation (uvx --from skills-ref agentskills)..."
if ! command -v uvx > /dev/null 2>&1; then
    echo "❌ uvx not found; cannot run the agentskills validation. Install uv: https://docs.astral.sh/uv/"
    ERRORS=$((ERRORS+1))
elif UV_CACHE_DIR=/tmp/uv-cache UV_TOOL_DIR=/tmp/uv-tools UV_TOOL_BIN_DIR=/tmp/uv-bin \
     uvx --from skills-ref agentskills validate "$SKILL_DIR"; then
    echo "✅ Agent Skills specification validation passed"
else
    echo "❌ Agent Skills specification validation failed"
    ERRORS=$((ERRORS+1))
fi

echo ""
echo "Validation complete:"
echo "  Errors: $ERRORS"
echo "  Warnings: $WARNINGS"

[ $ERRORS -eq 0 ] && exit 0 || exit 1
