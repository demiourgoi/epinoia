# Developer guide

## Agent skills

The skills in `.agents/skills` are for developing in this repo. The skills in `skills` are artifacts.

### Skills based on [Strands agents SOPs](https://github.com/strands-agents/agent-sop)

`skills/pdd` and `skills/codebase-summary` are modified derivatives;
`.agents/skills/agent-sop-author` is a verbatim copy. All remain licensed
under Apache-2.0 — see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).


### Skills based on [ponytail](https://github.com/dietrichgebert/ponytail)

None yet. Planned: a custom opencode agent based on a modification of an
agent skill from the ponytail repo (MIT-licensed). Follow the
[third-party checklist](#how-to-add-third-party-content-or-code-verbatim-or-modified)
when adding it.

## How To

### How to create a skill using agent SOPs

1. Create an agent SOP using `/agent-sop-author` providing a list of parameters, a list of steps, and some positive and negative examples. 
    - Ask `/agent-sop-author` to create the SOP on a directory `skill/my-skill` 
    - It is a also useful to consolidate an existing agent thread into an SOP.
2. [Convert the agent SOP into a skill](https://github.com/strands-agents/agent-sop#converting-sops-to-skills): `./bin/agent-sop-to-skill.sh my-skill`

Remember to favor generating deterministic scripts over skills or agent SOPs, when possible.

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
