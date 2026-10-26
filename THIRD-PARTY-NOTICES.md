# Third-Party Notices

This repository's MIT license (LICENSE) applies only to original content by
demiourgoi. The third-party components below keep their upstream licenses.
Attribution lives here and in a LICENSE sidecar inside each skill directory,
so it travels with the skill when the directory is copied elsewhere
(e.g. `cp -r skills/<name> ~/.agents/skills/`).

## Strands Agents — Agent SOPs

- Project: https://github.com/strands-agents/agent-sop
- Upstream copyright: Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
- License: Apache-2.0 — full text in LICENSES/Apache-2.0.txt

### Files in this repository

| File | Upstream source | Status |
| --- | --- | --- |
| `skills/pdd/SKILL.md` | `agent-sops/pdd.sop.md` | modified derivative |
| `skills/codebase-summary/SKILL.md` | `agent-sops/codebase-summary.sop.md` | modified derivative |
| `.agents/skills/agent-sop-author/` | `skills/agent-sop-author/` | modified derivative |

- `skills/pdd` and `skills/codebase-summary` were generated using
  `uvx strands-agents-sops skills` and then modified; their LICENSE sidecars
  state the modifications, as required by Apache-2.0 §4(b). Derivatives of
  Apache-2.0 work remain under Apache-2.0 and are not covered by this
  repository's MIT license.
- `.agents/skills/agent-sop-author` was downloaded directly from the
  upstream repo and then modified: the `SKILL.md` frontmatter was
  conformed to the Agent Skills specification, the body was reworked so
  the skill generates agent skills (`SKILL.md` plus deterministic logic
  in `scripts/`) instead of `.sop.md` SOP files, and `validate-sop.sh`
  was renamed to `validate-skill.sh` and extended with the skills-ref
  `agentskills validate` specification check. Its LICENSE sidecar
  states the modifications, as required by Apache-2.0 §4(b).

### Upstream NOTICE file (verbatim, per Apache-2.0 §4(d))

> Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

## Agent Skills specification

- Project: https://github.com/agentskills/agentskills
- Upstream copyright: Copyright 2025 Anthropic, PBC
- License: CC-BY-4.0 — full text in LICENSES/CC-BY-4.0.txt

### Files in this repository

| File | Upstream source | Status |
| --- | --- | --- |
| `.agents/skills/agent-sop-author/assets/agent-skills-specification.md` | `docs/specification.mdx`, published as https://agentskills.io/specification.md | verbatim copy of the published Markdown export |

- The upstream repository licenses its code under Apache-2.0 but its
  documentation under CC-BY-4.0 (see its README and `docs/LICENSE`). The
  specification is documentation, so this copy is attributed under
  CC-BY-4.0 rather than Apache-2.0.
- No upstream NOTICE file exists; attribution is provided by the
  `assets/LICENSE` sidecar and this section, as required by CC-BY-4.0 §3(a).

## ponytail

Project: https://github.com/dietrichgebert/ponytail (MIT)

No ponytail-derived content is included yet. Planned: a custom opencode
agent based on a modification of an agent skill from the ponytail repo.
Ponytail is MIT-licensed, so derivatives only need to retain the upstream
copyright and license notice; list the agent here when it is added.

## Adding third-party content

Use the `update-third-party-notices` skill
(`.agents/skills/update-third-party-notices/SKILL.md`) for the full
checklist; the entries above are examples of its output.
