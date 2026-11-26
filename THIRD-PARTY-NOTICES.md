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
  was renamed to `validate-skill.sh`, extended with the skills-ref
  `agentskills validate` specification check, and later rewritten in
  python3 as `validate-skill.py`, as required by the skill's own rule
  that scripts longer than 4 lines of bash MUST be python3, and a uv
  project skeleton (adapted from Harold's `harold-mcp/pyproject.toml`,
  without authors) was added under `assets/uv-project-skeleton/`. Its
  LICENSE sidecar states the modifications, as required by Apache-2.0
  §4(b).

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

- Project: https://github.com/DietrichGebert/ponytail
- Upstream copyright: Copyright (c) 2026 DietrichGebert
- License: MIT — full text in LICENSES/MIT.txt

### Files in this repository

| File | Upstream source | Status |
| --- | --- | --- |
| `skills/ponytail-review/SKILL.md` | `skills/ponytail-review/SKILL.md` | verbatim copy |
| `.opencode/agents/ponytail-review-readonly.md` | `skills/ponytail-review/SKILL.md` | modified derivative |

- `skills/ponytail-review` is the upstream skill copied verbatim: the
  `SKILL.md` is byte-identical to upstream and was deliberately left without
  frontmatter changes or in-file attribution, so it stays diffable against
  future upstream versions. The `LICENSE` sidecar next to it records the
  upstream copyright and the provenance, and travels with the skill when
  `make install` copies it elsewhere.
- The custom opencode agent was derived from the upstream `ponytail-review`
  agent skill: the skill frontmatter was dropped, the body became the agent's
  system prompt, a hard read-only restriction (with the review file as the
  single exception) was added, guidance for the three review subjects of
  `skills/ponytail-review-pdd` was added, and section 3 ("Check before you
  report") was kept verbatim. The LICENSE sidecar next to the agent states
  the modifications. MIT derivatives keep the upstream copyright and this
  notice; see `.opencode/agents/LICENSE`.
- The `skills/ponytail-review-pdd` skill that launches this agent is original
  demiourgoi content under this repository's MIT license.

## Aletheia web UI — bundled libraries (minified build output)

The Aletheia review web UI (`aletheia/webui/`, original demiourgoi sources
under this repository's MIT license) is compiled by Vite into committed
build output under `aletheia/src/aletheia_mcp/webui/dist/` so the
published wheel ships the GUI without requiring Node. Those chunks embed
minified code from the MIT-licensed libraries below; the build output is
generated, not copied from any upstream distribution.

### Bundled libraries

| Library | Upstream | Copyright | Status |
| --- | --- | --- | --- |
| `@codemirror/merge`, `@codemirror/state`, `@codemirror/view` | https://codemirror.net | Copyright (C) 2018-2022 by Marijn Haverbeke <marijn@haverbeke.berlin> and others | bundled minified |
| `react`, `react-dom` | https://react.dev | Copyright (c) Facebook, Inc. and its affiliates. | bundled minified |

Earlier revisions of this entry also bundled `@codemirror/language-data`
(plus the Lezer grammars it indexed) and `@uiw/react-codemirror`
(MIT per its package metadata; author: kenny wang <wowohoo@qq.com>; no
LICENSE file shipped); both were dropped from the MVP build in design
revision 3 (no language-dependent highlighting), and today's `dist/`
output contains none of their code.

### Files in this repository

| File | Upstream source | Status |
| --- | --- | --- |
| `aletheia/src/aletheia_mcp/webui/dist/**` | generated by `Makefile` target `webui` (Vite build of `aletheia/webui/`) | bundled build output embedding the libraries above |
| `aletheia/src/aletheia_mcp/webui/dist/LICENSE` | — | sidecar preserving the MIT copyright and permission notices of the bundled libraries; ships inside the wheel |
| `aletheia/src/aletheia_mcp/webui/dist/assets/README.md` | — | provenance note for the generated chunks |
| `aletheia/webui/dist-sidecar/LICENSE`, `aletheia/webui/dist-sidecar/assets/README.md` | — | source copies of the two files above (`make webui` regenerates the build output and copies them back in, so Vite's `emptyOutDir` cannot drop the notices) |

The MIT license requires the copyright and permission notice to travel
with copies or substantial portions of the software; that is satisfied by
`aletheia/src/aletheia_mcp/webui/dist/LICENSE` (also included in the
published wheel) and by this record.

## Adding third-party content

Use the `update-third-party-notices` skill
(`.agents/skills/update-third-party-notices/SKILL.md`) for the full
checklist; the entries above are examples of its output.
