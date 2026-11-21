# Ponytail review — implementation step 2 — round 1

> Review subject: `code-commits`, commit `fa6647f` (step 2 review core).
> opencode unavailable in this sandbox; ponytail checklist applied directly
> to the commit diff and the tests that exercise it.

What this change does: it adds the review domain: baseline snapshots with
a created-file marker, unified diffs with stable markers, sessions with a
pending/edited/approved/rejected status machine whose decisions write disk
effects first (atomic replace/delete; created files deleted on reject),
plus a bounded session store with deterministic hashed ids.

Checked: every status transition against the disk state it must leave; the
disambiguation-suffix branch; eviction; UTF-8/directory validation; the
atomicity claim under failure (parent missing leaves the original intact
and no temp file behind — tested). Expected load: one agent, one user, one
process — a lock per store is ample at this scale.

**Should fix:**

1. **`decide_all` can rollback files out of order under itself and re-raise
   mid-way** (`review/sessions.py`, `decide` + `decide_all`). What this
   is: the per-file `decide` takes the session lock per file. Problem: not
   a race for state (list is stable), but a mid-sequence OSError (disk
   full, read-only dir) leaves a half-applied "reject all" with files 1..k
   reverted and the rest pending, and the caller gets one error with no
   hint which files were reverted. Fix: none needed in the state machine
   (per-file atomicity is the meaningful unit for "reject all" — Zed's
   reject-all also applies file by file), but record it as accepted
   behavior in the GUI copy ("files are reverted in order; a failure stops
   the rest"). No code change in this step; the HTTP layer maps the
   partial failure per file.

2. **`ReviewSession.decide` re-raises OSError with no session context**
   (`review/sessions.py`). Problem: an HTTP 500 from a read-only
   directory says `PermissionError: ...` with no mention of which review
   action failed. Fix: wrap disk errors in a small `DiskEffectError`
   naming the file and the action, chaining the OSError. One class, one
   place.

3. **`compute_session_id` hashes absolute paths**
   (`review/diffs.py` + callers). Problem: the id (and the "reopen
   returns same session" guarantee) changes when the same project is
   reviewed from a different checkout path — harmless today (ids are
   process-local), but the design said canonical text uses the absolute
   path for sorting and the docstring promises stability across platforms
   for the *markers*, not the paths. Fix: none — document in the class
   docstring that ids are per-process (only used to address the in-memory
   session), so path-dependence has no external effect. Checked: no
   persistence uses the id.

Verdict: Ship 1 and 3 as documented decisions; fix 2 before step 3 so the
HTTP layer can map it — i.e. fix 2 first.
