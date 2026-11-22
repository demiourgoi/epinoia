# Design review — detailed-design-v3 (delta) — round 1

> ponytail checklist applied directly (opencode unavailable).
> Scope: the two deltas against v2 and idea-honing Q16–Q17.

What this change does: it compacts the diff UI, drops language-grammar
highlighting from the MVP, and adds an opt-in baseline-aware `edit` tool
with the Vibe built-in tool's schema and trusted-root criteria.

**Must fix:**

1. **`trusted_root` recomputation and drift are unspecified.** What this
   is: the design pins the root to the git root of the working directory
   at call time. Problem: `git_root()` shells out; recomputing it on every
   edit is a subprocess per tool call, and a repo discovered late or a
   stale rooted answer changes the security decision mid-process. Fix:
   compute the root **once** at service construction (the MCP process
   starts in the project directory), hold it immutable, and let the
   containment check use it. If the process starts outside a repo, the
   fallback root is the CWD — equally immutable. Document that a session
   is expected to start in the project (the same assumption all other
   tools already make when resolving relative paths).

2. **The edit evaluation order is not stated, so a failing edit could
   register a baseline.** Problem: baseline-then-edit without a stated
   order means a validation failure (0 matches, non-UTF-8, missing
   file) could leave a freshly registered baseline — a semantic change:
   every failed attempt would re-anchor the review round at unchanged
   content. Fix: state the order — trusted-root check → read and
   validate → baseline registration (only if absent) → atomic write.
   Failures leave the baseline untouched.

**Should fix:**

3. **The GUI compaction must pin specific CodeMirror classes**
   (`cm-gutters`, `cm-content`, the merge pane gap) rather than global
   padding changes, so a CodeMirror update cannot silently widen the UI
   again. Naming the classes here makes the review checkable.

Verdict: fix 1 and 2 in the doc, then ship.
