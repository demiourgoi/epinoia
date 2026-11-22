# Rough idea: Aletheia — Zed-style change review for CLI agents

Reproduce Zed's agent change review as an MCP server so terminal coding agents
(such as Mistral's Vibe CLI) get the same workflow:

- The agent edits files normally; the edits are already on disk, so linters and
  tests can run against them.
- The agent opens a review: the user gets a URL to a local web GUI that shows
  a side‑by‑side, syntax‑highlighted diff of every changed file.
- The user can approve each file or the whole set, or edit the changes in the
  GUI and then approve; edited content is written back to disk.
- Rejecting a file (or everything) rolls the file back to its pre‑agent
  content, directly on disk.
- Review never blocks the agent: the MCP tools return immediately; the agent
  polls a status tool if it wants to react to decisions.

Constraints given up front:

- MCP server in Python 3.14 (pinned) using FastMCP; command `aletheia`,
  packaged like `harold-mcp` (same author, installable with `uvx`).
- A local web server (port from an environment variable) serves the review
  GUI. The MCP layer itself is stateless; the web app keeps ephemeral in‑memory
  state via change sessions. The session URL encodes the session id; the id is
  a deterministic hash of the diff.
- The GUI must support syntax highlighting for popular languages (Java,
  Python, etc.). TypeScript + a modern build tool so the web app is packaged
  inside the `uvx` distribution.
- Developed in the `epinoia` repository under a new top‑level `aletheia`
  folder, following the PDD skill, with ponytail reviews of the design and of
  each implementation step (at most 3 review rounds each), one commit per PDD
  phase and per implementation step, and a final PR.
- The whole task is executed unattended: questions raised during PDD are
  answered by the agent using its best judgement and recorded as such.
