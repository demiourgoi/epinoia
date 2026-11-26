# Aletheia knowledge base — index

This directory is the agent-oriented knowledge base for the `aletheia/`
subproject of the epinoia repository: an MCP server that gives terminal
coding agents a Zed-style asynchronous change-review workflow (baseline →
live diff in a loopback web GUI → approve/reject per file).

**How to use this knowledge base.** Read this file first. It tells you which
document answers which kind of question; open that document instead of
scanning the source tree. If you are about to edit code, also read
`workflows.md` (how a change flows through the system) and
`components.md` (which module owns the behavior you are touching).

## Table of contents

| File | What it contains | Consult it when you need… |
| --- | --- | --- |
| [codebase_info.md](codebase_info.md) | Project identity, stack, layout, tooling | "What is this project?", "Where does X live?", "How do I run things?" |
| [architecture.md](architecture.md) | Process model, module map, design invariants (lazy server, in-memory baseline, trusted root, atomic writes) | "How is the server structured?", "Why is the web server started lazily?" |
| [components.md](components.md) | Each source module and the webui, with responsibilities and key symbols | "Which file implements the `edit` tool?", "Where do HTTP routes live?" |
| [interfaces.md](interfaces.md) | The MCP tool protocol, the HTTP API, the Vibe hook, and the CLI — exact request/response shapes | "What does `record_baseline` return?", "What are the `/api/*` routes?" |
| [data_models.md](data_models.md) | `Baseline`, the baseline store, review payload shapes, error taxonomy | "What does a creation marker mean?", "Which error does a missing baseline raise?" |
| [workflows.md](workflows.md) | End-to-end flows: record → edit → review → approve/reject; the `edit` tool flow; hook installation; GUI build | "What happens when the user clicks Reject?", "How does the GUI bundle get into the wheel?" |
| [dependencies.md](dependencies.md) | Runtime, dev, and GUI dependencies and why each is used | "Why FastMCP?", "What does the GUI use for the diff view?" |
| [review_notes.md](review_notes.md) | Consistency/completeness review of this knowledge base, gaps, recommendations | "Is anything here stale or missing?" |

## Relationships between documents

- `codebase_info.md` is the entry point: identity, stack, and layout.
- `architecture.md` builds on it with the process/module model and invariants.
- `components.md` maps every module to its file and responsibilities.
- `interfaces.md` and `data_models.md` are the two reference sheets for the
  wire and in-memory shapes; `components.md` tells you where each interface
  is implemented.
- `workflows.md` ties components and interfaces together into end-to-end
  flows.
- `dependencies.md` covers the external packages and the GUI toolchain.
- `review_notes.md` records known gaps in this documentation.

## Example queries and where to look

- "How do I add a new MCP tool?" → `components.md` (server/tools),
  `interfaces.md` (tool protocol), `workflows.md` (tool flow).
- "Where is the trusted-root check?" → `components.md` (`review/editing.py`),
  `architecture.md` (invariants).
- "What happens on reject of a created file?" → `workflows.md` (reject flow),
  `data_models.md` (creation marker).
- "How do I rebuild the GUI?" → `workflows.md` (GUI build), `codebase_info.md`
  (commands), `components.md` (`webui/`).
- "Why does the review page never go stale?" → `architecture.md` (live diff
  invariant), `workflows.md` (review flow).
