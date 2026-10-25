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
| `.agents/skills/agent-sop-author/` | `skills/agent-sop-author/` | verbatim copy |

- `skills/pdd` and `skills/codebase-summary` were generated using
  `uvx strands-agents-sops skills` and then modified; their LICENSE sidecars
  state the modifications, as required by Apache-2.0 §4(b). Derivatives of
  Apache-2.0 work remain under Apache-2.0 and are not covered by this
  repository's MIT license.
- `.agents/skills/agent-sop-author` was downloaded directly from the
  upstream repo and is unmodified; its licensing is recorded in REUSE.toml.

### Upstream NOTICE file (verbatim, per Apache-2.0 §4(d))

> Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

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
