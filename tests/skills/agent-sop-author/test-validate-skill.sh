#!/usr/bin/env bash
# Hermetic tests for .agents/skills/agent-sop-author/validate-skill.py:
# structural checks on fixture skills, guards, and the negative-constraint
# warning. Runs with a PATH that has no uvx, so no network is needed and
# the uvx-backed specification check is skipped deterministically.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../lib.sh"

VALIDATOR="$REPO_ROOT/.agents/skills/agent-sop-author/validate-skill.py"
WORK_DIR="$WORK_DIR/agent-sop-author"
mkdir -p "$WORK_DIR"

VALID_DIR="$WORK_DIR/valid-skill"
mkdir -p "$VALID_DIR"
cat > "$VALID_DIR/SKILL.md" <<'EOF'
---
name: valid-skill
description: A test skill with a description.
metadata:
  version: "1.0.0"
---
# Valid Skill

## Overview
Test.

## Parameters

- **a_param** (required): A thing.

**Constraints for parameter acquisition:**
- If all required parameters are already provided, You MUST proceed to the Steps
- If any required parameters are missing, You MUST ask for them before proceeding
- When asking for parameters, You MUST request all parameters in a single prompt
- When asking for parameters, You MUST use the exact parameter names as defined

## Steps

### 1. Do
Do it.

**Constraints:**
- You MUST do it because it matters

## Examples
- Example

## Troubleshooting
- Fix
EOF

# Skips the uvx specification check deterministically (hermetic: no network).
NO_UVX=(env PATH=/usr/bin:/bin)

group "valid skill: structural checks pass"

run "${NO_UVX[@]}" python3 "$VALIDATOR" "$VALID_DIR"
assert_rc_nonzero "exits non-zero only because uvx is absent (hermetic run)"
assert_grep "✅ Frontmatter present" "frontmatter check passes"
assert_grep "✅ Frontmatter field present: name" "name field reported"
assert_grep "✅ Frontmatter field present: description" "description field reported"
assert_grep "✅ Parameter constraints present" "parameter constraints check passes"
assert_grep "✅ Blank line after Parameters heading" "blank line check passes"
assert_grep "✅ Numbered steps present" "numbered steps check passes"
assert_grep "✅ Constraints sections present" "constraints check passes"
assert_grep "✅ RFC 2119 keywords present" "RFC 2119 check passes"
assert_not_grep "Negative constraints found" "no negative-constraint warning for 'because' context"
assert_grep "❌ uvx not found" "uvx absence is reported as an error"

group "bad name and missing sections are caught"

BAD_DIR="$WORK_DIR/1_bad-name"
mkdir -p "$BAD_DIR"
sed -e 's/^name: valid-skill/name: Bad_Name/' "$VALID_DIR/SKILL.md" > "$BAD_DIR/SKILL.md"
run "${NO_UVX[@]}" python3 "$VALIDATOR" "$BAD_DIR"
assert_rc 1 "invalid skill exits 1"
assert_grep "must use lowercase letters, numbers and hyphens" "bad name rejected"
assert_grep "must match the skill directory name" "name/directory mismatch rejected"

MISSING_DIR="$WORK_DIR/2_missing-sections"
mkdir -p "$MISSING_DIR"
printf -- '---\nname: 2-missing-sections\ndescription: Sections missing.\n---\n# T\n\n## Overview\nO\n' > "$MISSING_DIR/SKILL.md"
run "${NO_UVX[@]}" python3 "$VALIDATOR" "$MISSING_DIR"
assert_rc 1 "skill with missing sections exits 1"
assert_grep "Missing required section: Parameters" "missing Parameters reported"
assert_grep "Missing required section: Steps" "missing Steps reported"
assert_grep "No numbered steps found" "missing numbered steps reported"
assert_grep "No Constraints sections found" "missing Constraints reported"

group "parameter structure errors are caught"

PARAMS_DIR="$WORK_DIR/3-bad-params"
mkdir -p "$PARAMS_DIR"
python3 - "$VALID_DIR/SKILL.md" "$PARAMS_DIR/SKILL.md" <<'PY'
import re
import sys
from pathlib import Path

t = Path(sys.argv[1]).read_text()
t = t.replace("## Parameters\n\n", "## Parameters\n", 1)  # drop blank line
i = t.find("**Constraints for parameter acquisition:**")   # drop constraints block
j = t.find("## Steps", i)
t = t[:i] + t[j:]
t = t.replace("name: valid-skill", "name: 3-bad-params")
Path(sys.argv[2]).write_text(t)
PY
run "${NO_UVX[@]}" python3 "$VALIDATOR" "$PARAMS_DIR"
assert_rc 1 "bad parameters structure exits 1"
assert_grep "missing 'Constraints for parameter acquisition'" "missing parameter constraints reported"
assert_grep "must have blank line after heading" "missing blank line reported"

group "negative-constraint warning honors all context words"

AS_DIR="$WORK_DIR/4-as-context"
mkdir -p "$AS_DIR"
sed -e 's/^name: valid-skill/name: 4-as-context/' -e 's/because it matters/as this could corrupt history/' "$VALID_DIR/SKILL.md" > "$AS_DIR/SKILL.md"
run "${NO_UVX[@]}" python3 "$VALIDATOR" "$AS_DIR"
assert_not_grep "Negative constraints found" "'as' counts as context"

AVOID_DIR="$WORK_DIR/5-to-avoid"
mkdir -p "$AVOID_DIR"
sed -e 's/^name: valid-skill/name: 5-to-avoid/' -e 's/because it matters/to avoid losing data/' "$VALID_DIR/SKILL.md" > "$AVOID_DIR/SKILL.md"
run "${NO_UVX[@]}" python3 "$VALIDATOR" "$AVOID_DIR"
assert_not_grep "Negative constraints found" "'to avoid' counts as context"

BARE_DIR="$WORK_DIR/6-bare-negative"
mkdir -p "$BARE_DIR"
sed -e 's/^name: valid-skill/name: 6-bare-negative/' -e 's/- You MUST do it because it matters/- You MUST NOT skip validation/' "$VALID_DIR/SKILL.md" > "$BARE_DIR/SKILL.md"
run "${NO_UVX[@]}" python3 "$VALIDATOR" "$BARE_DIR"
assert_grep "Negative constraints found without context" "context-free negative constraint warned"

group "guards"

run "${NO_UVX[@]}" python3 "$VALIDATOR" "$WORK_DIR/does-not-exist"
assert_rc 1 "missing skill directory exits 1"
assert_grep "Skill directory not found" "missing directory error message"

run "${NO_UVX[@]}" python3 "$VALIDATOR"
assert_rc 1 "no arguments exits 1"
assert_grep "Usage: .*validate-skill\.py" "no arguments prints usage"

NO_MD_DIR="$WORK_DIR/7-no-skill-md"
mkdir -p "$NO_MD_DIR"
run "${NO_UVX[@]}" python3 "$VALIDATOR" "$NO_MD_DIR"
assert_rc 1 "skill directory without SKILL.md exits 1"
assert_grep "Missing required file" "missing SKILL.md error message"

echo
echo "Test workspace (kept for inspection): $WORK_DIR"
finish
