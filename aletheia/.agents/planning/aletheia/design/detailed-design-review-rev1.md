# Design review — detailed-design.md — round 1

> Reviewed per `skills/ponytail-review` (`ponytail-review-pdd` subject:
> `tech-design`). The `opencode` runner is unavailable in this sandbox, so
> this review was produced by the implementing agent applying the ponytail
> checklist directly to `design/detailed-design.md`; all findings were then
> incorporated.

What this change does: it designs an MCP server + loopback web GUI that lets
a terminal agent record file baselines, apply edits on disk, then hand the
user a URL to approve/edit/reject those edits, with rejections rolled back
onto disk immediately.

**Must fix:**

1. **Editing then rejecting loses the chance to approve the edit cleanly**
   (`Data Models` / `R5`). What this is: the file status machine. Problem:
   the design says `save_edit` is illegal on a decided file but then shows
   `edited` as an end state, and `approve_all` isn't defined for files whose
   content the user just edited. If `edited` is a final decision, the user
   cannot keep tweaking before approving; if it is not, `all_approved` can
   never be reached after an edit. Fix: make `edited` a *pending* state: the
   only decided states are `approved` and `rejected`; `save_edit` is allowed
   while `pending|edited`, and `approve`/`reject` (and the `_all` variants)
   accept files in `pending|edited`. If we skip it: the primary Zed workflow
   (edit the diff, then approve) has no defined path.

2. **Concurrent mutation is unspecified** (Architecture). What this is: the
   web thread handles user decisions while the stdio tool thread may open
   new sessions and record baselines. Problem: two threads touch the
   baseline and session stores; Python dict ops are atomic but
   check-then-act sequences (create-if-absent id, decide-then-mutate) are
   not, so a decision can interleave with eviction or creation. Fix: state a
   single `threading.Lock` (or per-store lock) rule: every store method is
   executed under it, and disk writes happen inside the lock to keep
   "state follows disk" atomic per decision. If we skip it: rare
   unexplainable session corruption for a concurrent user.

3. **The server-start race/error contract is under-specified** (R4, web
   layer). What this is: lazy `uvicorn` start in a daemon thread. Problem:
   `open_review` returns a URL before the socket is accepting; a fast user
   clicking it can hit connection refused, and a second `open_review` during
   a failing start must see the real error. Fix: wait (bounded, seconds) for
   a startup event; on bind failure return `ServerStartError` (not a stale
   success), reuse a single well-known server instance with an idempotent
   `ensure_started`. If we skip it: the first user of a session sometimes
   gets a dead link, and port errors surface as confusing timeouts.

**Should fix:**

4. **Overall `mixed` is meaningless** (R6). Problem: with per-file decisions,
   "mixed" (some approved, some rejected) is indistinguishable from pending
   for the agent. Fix: report `pending` while any file is undecided, plus a
   per-file map; drop "mixed" or define it as "all decided but not all the
   same decision". The design text already half-says the latter — say it
   once, precisely.

5. **Session id canonicalization must include new-file markers. What this
   is: the diff hash. Problem: a created file produces a baseline of
   `None`; the canonical text must be stable for that case (e.g. literal
   `<created>` stem) or the hash differs across platforms by accident.
   Fix: name the canonical encoding explicitly.

6. **`save_edit` on a file that was deleted at open time** is unspecified
   and ambiguous with the "parent directories are never created" rule.
   Fix: allow it (write edited content; the parent existed when the file
   was created) and say so.

**Nice to have:**

7. Record the out-of-scope note that the agent may keep editing files while
   the review is open; the GUI reviews the snapshot at open time, not live.

Verdict: fix 1, 2 and 3 first.
