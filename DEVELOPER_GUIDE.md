# Developer guide

## Agent skills

The skills in `.agents/skills` are for developing in this repo. The skills in `skills` are artifacts.

### Skills based on [Strands agents SOPs](https://github.com/strands-agents/agent-sop)

The agent skills `codebase-summary` and `pdd` have been generated using `uvx strands-agents-sops skills`, and then modified.

`agent-sop-author` was downloaded directly from [the repo](https://github.com/strands-agents/agent-sop/tree/main/skills/agent-sop-author)


### Skills based on [ponytail](https://github.com/dietrichgebert/ponytail)

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
