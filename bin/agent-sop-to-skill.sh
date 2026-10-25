#!/usr/bin/env bash
#
# Convert the Agent SOPs in skills/<skill-name> into a skill, in place.
#
# Usage: bin/agent-sop-to-skill.sh <skill-name>
#
# Example: bin/agent-sop-to-skill.sh edenai-zed-config
#
# Generated files overwrite existing ones in skills/<skill-name>; the source
# *.sop.md files are left in place so they can be reviewed and removed by hand.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: ${0##*/} <skill-name>" >&2
  exit 2
fi

name=$1
skills_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)/skills
skill_dir=${skills_dir}/${name}

if [[ ! -d $skill_dir ]]; then
  echo "error: no such directory: ${skill_dir}" >&2
  exit 1
fi

temp_dir=$(mktemp -d)
trap 'rm -rf -- "$temp_dir"' EXIT

uvx strands-agents-sops skills --sop-paths "$skill_dir" --output-dir "$temp_dir"
cp -a -- "${temp_dir}/${name}/." "$skill_dir/"

shopt -s nullglob
sop_files=("$skill_dir"/*.sop.md)

printf 'Review %s/SKILL.md and consider deleting the following files:\n' "$skill_dir"
printf '  %s\n' "${sop_files[@]:-none found}"
printf 'If %s derives from a third-party project: add a LICENSE sidecar, set the frontmatter license field, and list it in THIRD-PARTY-NOTICES.md\n' "$name"
