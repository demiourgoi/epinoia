# Ponytail review — detailed design, round 1

What this change does: this document specifies azathoth, a localhost-only
OpenAI-compatible chat completions proxy that forwards prompts to an ACP
agent (`vibe-acp` by default) with every tool channel disabled from the
client side.

Findings (all fixed into the design before implementation):

1. **Must fix — cross-streamed updates** — the single ACP connection is
   shared by concurrent requests, but the design did not say how
   `session_update` notifications reach the right request. Without routing
   by `session_id`, one conversation can receive another's text. Fixed: the
   bridge demultiplexes updates by `session_id` into per-request queues.
2. **Should fix — timeout leaves the agent turn running** — the design
   proposed cancelling the in-flight prompt, but the SDK exposes no session
   cancel; the agent would keep generating. Fixed: on timeout the request
   fails with `502` and the bridge connection is reopened before the next
   request, discarding the runaway turn with the old process.
3. **Nice to have — `metadata.py` is YAGNI** — a module that only returns
   the version. Fixed: deleted from the design; the version is read via
   `importlib.metadata` like the harold-mcp reference does.

Verdict: fix 1 and 2 first — done in this round; design updated accordingly.
Lean: -20 lines possible (finding 3).
Not checked: behavior of real `vibe-acp` config-option names beyond the
requester's research; integration tests will cover them.
