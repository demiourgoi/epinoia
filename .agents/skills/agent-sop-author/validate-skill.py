#!/usr/bin/env python3
"""Validate an agent skill created with the agent-sop-author skill.

Checks:
1. Agent Skills format basics: SKILL.md present, YAML frontmatter with
   required name/description fields, name matching the directory name
2. SOP prompt structure inside SKILL.md (Overview, Parameters,
   Steps with numbered sub-steps and Constraints, RFC 2119 keywords)
3. Agent Skills specification compliance, authoritatively checked with
   the skills-ref reference library (uvx --from skills-ref agentskills)

Usage: validate-skill.py <path-to-skill-directory>
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STEP_RE = re.compile(r"^### \d+\.", re.MULTILINE)
CONSTRAINTS_RE = re.compile(r"^\*\*Constraints:\*\*", re.MULTILINE)
RFC2119_RE = re.compile(r"You (MUST|SHOULD|MAY)\b")
NEGATIVE_RE = re.compile(r"You (MUST NOT|SHOULD NOT)(?!.*\b(because|since)\b)")


def count_frontmatter_boundary(lines: list[str]) -> bool:
    return bool(lines) and lines[0].strip() == "---"


def extract_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not count_frontmatter_boundary(lines):
        return ""
    out = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        out.append(line)
    return "\n".join(out)


def frontmatter_field(frontmatter: str, field: str) -> str:
    match = re.search(rf"^{field}:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else ""


def section_present(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.MULTILINE) is not None


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-skill-directory>")
        return 1

    skill_dir = Path(sys.argv[1]).resolve()
    errors = 0
    warnings = 0


    if not skill_dir.is_dir():
        print(f"❌ Skill directory not found: {skill_dir}")
        return 1

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        print(f"❌ Missing required file: {skill_file}")
        return 1

    print(f"Validating skill: {skill_dir}")
    print("")

    text = skill_file.read_text(encoding="utf-8")
    frontmatter = extract_frontmatter(text)

    # --- Agent Skills format: frontmatter ---

    if count_frontmatter_boundary(text.splitlines()):
        print("✅ Frontmatter present")
    else:
        print("❌ SKILL.md must start with a YAML frontmatter block delimited by ---")
        errors += 1

    if re.search(r"^description:", frontmatter, re.MULTILINE):
        print("✅ Frontmatter field present: description")
    else:
        print("❌ Frontmatter missing required field: description")
        errors += 1

    skill_name = frontmatter_field(frontmatter, "name")
    dir_name = skill_dir.name

    if skill_name:
        print("✅ Frontmatter field present: name")
        if not NAME_RE.match(skill_name):
            print(f"❌ name '{skill_name}' must use lowercase letters, numbers and hyphens only, must not start or end with a hyphen and must not contain consecutive hyphens")
            errors += 1
        if len(skill_name) > 64:
            print(f"❌ name '{skill_name}' exceeds 64 characters")
            errors += 1
        if skill_name != dir_name:
            print(f"❌ name '{skill_name}' must match the skill directory name '{dir_name}'")
            errors += 1
    else:
        print("❌ Frontmatter missing required field: name")
        errors += 1

    description = frontmatter_field(frontmatter, "description")
    if description and len(description) > 1024:
        print("❌ description exceeds 1024 characters")
        errors += 1

    # --- SOP prompt structure (body of SKILL.md) ---

    for section, pattern in [
        ("Title (H1)", r"^# "),
        ("Overview", r"^## Overview"),
        ("Parameters", r"^## Parameters"),
        ("Steps", r"^## Steps"),
    ]:
        if section_present(text, pattern):
            print(f"✅ Section present: {section}")
        else:
            print(f"❌ Missing required section: {section}")
            errors += 1

    if section_present(text, r"^## Parameters"):
        params_block = re.search(r"^## Parameters.*?(?=\n## |\Z)", text, re.MULTILINE | re.DOTALL)
        if params_block and "Constraints for parameter acquisition" in params_block.group(0)[:2000]:
            print("✅ Parameter constraints present")
        else:
            print("❌ Parameters section missing 'Constraints for parameter acquisition'")
            errors += 1

        heading = re.search(r"^## Parameters$", text, re.MULTILINE)
        after = heading.end()
        if heading and text.find("\n\n", after) == after:
            print("✅ Blank line after Parameters heading")
        else:
            print("❌ Parameters section must have blank line after heading")
            errors += 1

    if STEP_RE.search(text):
        print("✅ Numbered steps present")
    else:
        print("❌ No numbered steps found (format: ### 1. Step Name)")
        errors += 1

    if CONSTRAINTS_RE.search(text):
        print("✅ Constraints sections present")
    else:
        print("❌ No Constraints sections found in steps")
        errors += 1

    if RFC2119_RE.search(text):
        print("✅ RFC 2119 keywords present")
    else:
        print("⚠️  No RFC 2119 keywords found (MUST, SHOULD, MAY)")
        warnings += 1

    if NEGATIVE_RE.search(text):
        print("⚠️  Negative constraints found without context (add 'because', 'since', etc.)")
        warnings += 1

    if not section_present(text, r"^## Examples"):
        print("⚠️  Recommended section missing: Examples")
        warnings += 1

    if not section_present(text, r"^## Troubleshooting"):
        print("⚠️  Recommended section missing: Troubleshooting")
        warnings += 1

    skill_lines = text.count("\n") + 1
    if skill_lines > 500:
        print(f"⚠️  SKILL.md has {skill_lines} lines; keep it under 500 and move detail to references/")
        warnings += 1

    # --- Agent Skills specification validation (authoritative) ---

    print("")
    print("Running Agent Skills specification validation (uvx --from skills-ref agentskills)...")
    if shutil.which("uvx") is None:
        print("❌ uvx not found; cannot run the agentskills validation. Install uv: https://docs.astral.sh/uv/")
        errors += 1
    else:
        env = os.environ.copy()
        env.update({
            "UV_CACHE_DIR": "/tmp/uv-cache",
            "UV_TOOL_DIR": "/tmp/uv-tools",
            "UV_TOOL_BIN_DIR": "/tmp/uv-bin",
        })
        result = subprocess.run(
            ["uvx", "--from", "skills-ref", "agentskills", "validate", str(skill_dir)],
            env=env,
        )
        if result.returncode == 0:
            print("✅ Agent Skills specification validation passed")
        else:
            print("❌ Agent Skills specification validation failed")
            errors += 1

    print("")
    print("Validation complete:")
    print(f"  Errors: {errors}")
    print(f"  Warnings: {warnings}")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
