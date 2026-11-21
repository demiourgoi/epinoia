# Research: Zed's agent change review model

Sources:
- [Zed Agent Panel docs](https://zed.dev/docs/ai/agent-panel)
- [Zed editor overview](https://zed.dev/ai)
- [Zed issue #50142](https://github.com/zed-industries/zed/issues/50142),
  [discussion #47695](https://github.com/zed-industries/zed/discussions/47695),
  [discussion #31265](https://github.com/zed-industries/zed/discussions/31265)
- [DeepWiki: agent_ui crate](https://deepwiki.com/zed-industries/zed/8.1-agent-panel-and-ui)

## Findings

- Zed's agent edits are applied to the project files immediately. The
  "Review Changes" flow (AgentDiffPane, a multi-buffer pane) shows the
  resulting diffs **after** they are on disk.
- The review UI lets the user **accept or reject each file's changes**, or
  **the whole set**, and also **edit** the changes inline (the diff is an
  "editable unified diff" per zed.dev/ai).
- **Reject reverts the file on disk** to its pre-change content (Zed's
  reject/remove controls; the git panel's equivalent is "RestoreFile").
- The review is **not blocking**: the conversation and the tool work continue
  while the user reviews; the review pane overlays the normal buffers.
- Zed renders syntax with Tree-sitter everywhere, and its diff engine tracks
  changed chunks per file.
- Known pain points (issues above): review state vs git staging, external
  agents lacking the diff pane (ACP limitation) — exactly the gap Aletheia
  fills for terminal agents: the agent has no GUI, but it can drive an MCP
  server that provides one.

## Implications for our design

1. Changes on disk at review time is the correct model — the agent can lint.
2. The MCP layer must not block on review; a status tool mirrors the
   non-blocking pane.
3. Per-file accept/reject semantics with immediate on-disk revert, plus
   in-GUI editing of the proposed content, capture the core Zed workflow.
4. Hunk-level accept/reject (Zed granularity) is out of scope for v1; v1 is
   file-level, with free editing inside the diff editor as the escape hatch.

## Zed flow vs Aletheia flow

```mermaid
sequenceDiagram
    participant U as User
    participant A as CLI agent (Vibe)
    participant M as Aletheia MCP (stdio)
    participant W as Aletheia web GUI (loopback HTTP)
    A->>M: record_baseline(files)
    A->>A: edits files on disk (runs linters)
    A->>M: open_review(files)
    M-->>A: session_id + review URL (no blocking)
    A->>U: shows URL to open
    U->>W: opens URL, sees highlighted diffs
    U->>W: approve / edit+save / reject (per file or all)
    W->>W: approved kept; edited written to disk; rejected reverted on disk
    A->>M: get_review_status(session_id)
    M-->>A: per-file decisions (e.g. file X rejected/reverted)
```
