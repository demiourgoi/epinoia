# Design review — detailed-design-v2 — round 1

> ponytail checklist applied directly (opencode unavailable in this
> sandbox). Scope: the v2 design document against the v2 requirements in
> idea-honing Q12–Q15 and against revision 1 for what must actually be
> deleted.

What this change does: it redesigns the review model from sessions to a
single baseline: constant URL, free port, live diff, decisions shrink the
baseline (approve=remove, reject=rollback+remove), plus the v1 hook idea.

Checked: the status machine really disappears (no derived 409s anywhere);
rollback ordering (disk effect before entry drop) keeps "state follows
disk"; the free-port contract covers the same failure modes revision 1
fixed (accepting URL, fast bind failure); tool/REST parity keeps agent and
browser workflows symmetric.

**Should fix:**

1. **`get_change_status` must stay cheap on every poll** — with live
   diffs, a chatty agent polling a large baseline re-reads every file each
   time. Problem: real slowdowns for large changesets are possible at the
   expected load. Fix: state in the design that status (R6) reports kinds
   and `changed` flags only (read file sizes/content once per call, no
   unified-diff computation, no content in the payload); full contents +
   diffs are only computed for `review_payload()` (GUI). Acceptable at
   this scale; says the worst case out loud.
2. **Save-edit on a deleted-on-disk file conflicts with the atom-writer
   contract.** What this is: R5's Save edit writes edited content, but a
   creation-marker file whose parent directory vanished (agent deleted a
   dir) now fails during a user decision with a raw OSError in the GUI.
   Fix: reuse the DiskEffectError wrap (400-or-500 mapping with file and
   action named) — already half-stated in Error Handling; make it apply to
   save-edit too.
3. **Hook payload robustness is unspecified.** What this is: R8 reads
   "the edited path" but the built-in tools' argument keys vary (`edit`
   vs `write_file`). Fix: name the extraction rule — try `file_path`,
   `path`, `filename`, skip silently otherwise (hooks tolerate unknown
   input; `strict=false` default keeps failures as warnings not denials).

Nothing else found after tracing the approve-all/reject-all paths, the
empty-baseline states (GUI and status), and re-record mid-review.

Verdict: fix 1–3 in the doc, then ship.
