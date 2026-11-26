# Rough Idea

Implement an agent skill named `mistral-vibe-cli` in the `skills/` directory of
the `epinoia` repository. The skill is a port of the Hermes Agent
`opencode` optional skill
(https://github.com/NousResearch/hermes-agent/tree/main/optional-skills/autonomous-ai-agents/opencode),
adapted from the OpenCode CLI to the Mistral Vibe CLI
(https://github.com/mistralai/mistral-vibe). The skill allows an agent to
delegate coding tasks to the Mistral Vibe CLI: run bounded one-shot coding
tasks programmatically, review results, iterate on saved sessions, and run
isolated parallel tasks.

Follow the Agent Skills specification (https://agentskills.io/specification.md):
a skill directory with a `SKILL.md` containing YAML frontmatter
(`name` matching the directory, `description`, optional `license`,
`compatibility`, `metadata`).

Update the install target in the `Makefile` so the new skill is also
installed. All PDD artifacts and code comments must be in English.

References:
- Mistral Vibe CLI docs: https://docs.mistral.ai/llms/vibe/code/llms.txt
- Mistral Vibe source: https://github.com/mistralai/mistral-vibe
