# Step 1 Review — rev1

Reviewer: ponytail-review, applied to `skills/mistral-vibe-cli/SKILL.md`
(commit 5a4bc89). Load assumption: an agent delegating coding tasks, one
session per repository, informal single-user scale.

**What this change does:** Adds a 296-line SOP skill teaching agents to
delegate coding to the Mistral Vibe CLI: readiness checks, bounded
programmatic runs, exit-code triage, session continuation, parallel
worktrees, and self-verification.

## Must fix

1. **The parallel-task examples start the interactive TUI, which the skill
   itself forbids** (`## Examples` → "Parallel isolated tasks")
   - **What this is:** Two example invocations for isolated parallel tasks.
   - **Problem:** `vibe "Fix issue #101 and commit" --worktree issue-101`
     passes the prompt positionally, which is the *interactive* form; a
     non-interactive agent that runs it gets a TUI it cannot drive. The
     skill's step 1 says to use programmatic mode only, so the skill's own
     example violates its own rule.
   - **Fix:** Use the programmatic form in both examples:
     `vibe --prompt "Fix issue #101 and commit" --worktree issue-101`.
   - **If we skip it:** An agent following the example hits a hung TUI on
     its first parallel delegation.

## Should fix

2. **The Overview overpromises a JSON transcript on every run** (Overview)
   - **What this is:** The last Overview sentence says a programmatic run
     "exits with a final answer, a JSON transcript, and a documented exit
     code".
   - **Problem:** The JSON transcript only appears with
     `--output json|streaming`; the default output is plain text of the
     final answer. A reader will look for JSON that is not there.
   - **Fix:** Say "the final answer (or a JSON transcript with
     `--output json`) and a documented exit code".

3. **The `@path` example explains nothing** (`## Examples` → "Reference
   files in a prompt")
   - **What this is:** A sentence suggesting `@path` references.
   - **Problem:** It neither shows an example nor states the limitation
     (the docs describe `@` completion in interactive mode; `@path` in a
     programmatic prompt works as plain text the model reads). As written it
     is dead prose.
   - **Fix:** Show a concrete prompt using `@src/agent.py`, or delete the
     entry.

## Nice to have

4. **The `VIBE_SESSION=1` bullet is muddled** (step 3, last constraint)
   - **What this is:** A constraint about the environment variable Vibe
     sets on commands it runs.
   - **Problem:** "You SHOULD record `VIBE_SESSION=1` awareness" is not an
     actionable instruction; "so can you when checking logs" has no
     mechanism.
   - **Fix:** State the fact once: commands Vibe runs get `VIBE_SESSION=1`
     in their environment, so logs and hooks scripts can detect a Vibe run.

**Verdict: fix 1 and 2 first.**
