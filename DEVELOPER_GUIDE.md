# Developer guide

## Agent skills

The skills in `.agents/skills` are for developing in this repo. The skills in `skills` are artifacts.

### Skills based on [Strands agents SOPs](https://github.com/strands-agents/agent-sop)

`skills/pdd` and `skills/codebase-summary` are modified derivatives, and
so is `.agents/skills/agent-sop-author` (it now generates agent skills
instead of `.sop.md` SOP files). All remain licensed under Apache-2.0 —
see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).


### Skills based on [ponytail](https://github.com/dietrichgebert/ponytail)

`.opencode/agents/ponytail-review-readonly.md` is a custom opencode agent
derived from a modification of the `ponytail-review` agent skill of the
ponytail repo (MIT-licensed): the skill body became the agent's system
prompt with a hard read-only restriction, and section 3 ("Check before you
report") was kept verbatim. Its read-only permissions live in `opencode.json`
(`agents.ponytail-review-readonly.permissions`), which also ships the agent.
`skills/ponytail-review-pdd` is the skill that launches the agent to review
PDD artifacts; its tests live in `tests/skills/ponytail-review-pdd`. See
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for attribution.

## How To

### How to create a skill

1. Ask `/agent-sop-author` to create the skill, providing a list of parameters, a list of steps, and some positive and negative examples.
    - The skill is generated directly in the Agent Skills format: a `skill-name/` directory with a `SKILL.md` (frontmatter plus SOP prompt body) and deterministic logic in `scripts/`.
    - It is also useful to consolidate an existing agent thread into a skill.
2. Validate with `.agents/skills/agent-sop-author/validate-skill.sh <skill-dir>` (e.g. `skills/my-skill`).

Remember to favor deterministic scripts in `scripts/` over prose instructions in the SKILL.md, when possible.

### How to run the tests

`make test` (or `tests/run.sh`) runs every hermetic test suite in `tests/`;
suites are any `test-*.sh` files and new ones are picked up automatically.
`make test-e2e` additionally runs the live opencode smoke tests, which need
opencode authentication and spend a few cents of tokens; full LLM reviews are
deliberately not automated because they cost real reasoning money. See
[tests/README.md](tests/README.md) for details.

### How to setup Zed for an EdenAI model

On `~/.config/zed/settings.json` add an entry 

```json
    "openai_compatible": {
      "EdenAI": {
        "api_url": "https://api.eu.edenai.run/v3",
        "available_models": [

        ],
      },
    },
```

This is using the [EdenAI EU endpoint](https://www.edenai.co/docs/v3/data-governance/eu-endpoint). Then filter for Europe region in the [model list](https://app.edenai.run/models?regions=eu&q=deepseek).  
Install the config generation skill with `cp -r skills/edenai-zed-config ~/.agents/skills/`, and add to `available_models` the configuration generated in a Zed thread for:

> /edenai-zed-config for the model YOUR_MODEL_ID

### How to add third-party content or code (verbatim or modified)

Use the `update-third-party-notices` skill
(`.agents/skills/update-third-party-notices/SKILL.md`) whenever third-party
content or code is reused in this repository, verbatim or modified — for
example when the planned custom opencode agent based on a modified ponytail
agent skill is added. The skill runs the full compliance workflow: verify
the upstream license (stop on copyleft), add the `LICENSES/<SPDX-ID>.txt`
text, keep verbatim files byte-identical, add `LICENSE` sidecars and the
`license` frontmatter field for modified derivatives, update
`THIRD-PARTY-NOTICES.md` and `REUSE.toml`, and validate with
`uvx reuse lint`.
