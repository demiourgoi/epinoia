# Design review — detailed-design.md — round 2

> Same setup as round 1: ponytail checklist applied directly (opencode
> runner unavailable in this sandbox). Round‑1 findings 1–7 were verified as
> incorporated before this review.

What this change does: after round 1 it now defines a complete status machine
(edited is pending; only approved/rejected are decided), a locking rule for
the two shared threads, a startup contract for the lazy web server, a stable
canonical form for the session id, and precise status/409 semantics.

Checked: the status machine covers every GUI action sequence
(edit→edit, edit→approve, edit→reject, double-approve, post-decision edit),
the locking rule covers baseline, session and disk-effect paths, the
web-server contract prevents stale URLs, requirements R1–R9 map to
components that exist in the architecture, and the out-of-scope list
matches what the components actually do. No concrete failure case found.
Two minor ambiguities were tightened in place while re-checking (decided
file reached via `approve_all` when an edit was saved mid-flight is defined:
`_all` variants act only on undecided files; `save_edit` on an absent file).

Looks good. Ship.
