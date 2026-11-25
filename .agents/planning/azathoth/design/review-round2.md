# Ponytail review — full implementation, round 2

What this change does: adds the complete azathoth service — an
OpenAI-compatible chat completions endpoint (JSON + SSE) that connects to an
ACP agent (`vibe-acp` by default) and disables every tool channel from the
client side — plus hermetic tests against a scripted fake agent.

Findings (fixed in this round):

1. **Must fix — agent-side errors leaked through as 500s** — an
   ACP `RequestError` (agent crashed mid-turn) escaped the bridge untyped,
   producing a `500` instead of a `502` and aborting SSE streams without
   the `data: [DONE]` terminator. Fixed: `RequestError` is now mapped to
   `AcpBridgeError` at both bridge boundaries, covered by new unit tests
   (`FAIL` fake-agent behavior: 502 non-streaming, closed-with-`[DONE]`
   streaming).
2. **Should fix — `stream()` exceeded the complexity gate** — the update
   pump and session lifecycle shared one function. Fixed by extracting
   `_pump()` (queue-draining inner generator) and the shared
   `_message_text()` helper; behavior unchanged, tests still green.

Not checked: behavior against a real `vibe-acp` build (no credentials in
this environment); the opt-in integration test covers it for operators who
have one.

Verdict: Ship.
Lean: functions smaller, no dead code found (the step-1 temporary deptry
ignore was already removed in step 4).
