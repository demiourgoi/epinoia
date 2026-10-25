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

Before copying content or code from another project:

1. Identify the upstream license (SPDX identifier) and, if upstream ships a
   NOTICE file, keep its content verbatim (Apache-2.0 §4(d)).
2. Add the full license text to `LICENSES/<SPDX-ID>.txt` if not present
   (e.g. `LICENSES/Apache-2.0.txt`).
3. Verbatim copies: keep the files byte-identical to upstream (no added
   headers or edits), so they stay diffable; record their licensing in
   `REUSE.toml` and `THIRD-PARTY-NOTICES.md` instead of in the files.
4. Modified or derived content: keep it under its upstream license (an
   Apache-2.0 derivative stays Apache-2.0; MIT content can be distributed
   under this repo's MIT license as long as the upstream notice is kept).
   Add a `LICENSE` sidecar in the same directory stating the upstream
   copyright, your copyright for the modifications, and what changed
   (Apache-2.0 §4(b)). For skills, also set the `license` field in the
   `SKILL.md` frontmatter — never add attribution text to the skill body,
   because the whole file is loaded into the agent's context.
5. List the content in `THIRD-PARTY-NOTICES.md` (upstream source, license,
   status: verbatim or modified).
6. Add a `REUSE.toml` annotation for files without in-file SPDX headers and
   validate with `uvx reuse lint`.
7. Copyleft content (GPL family): do not add without checking first — this
   repository is MIT-licensed and GPL code cannot be relicensed under MIT.
