# Ponytail review — rev2 step 6 (baseline-only core) — round 2

> Fix 1 verified: all URL-bearing service calls now go through
> `ensure_running` (server starts lazily with the first URL anyone asks
> for); `current_url` and its `:0` fallback are deleted; the e2e test
> asserts the URL equals the real bound socket URL.

Checked: rollback ordering (disk effect under the operation lock, entry
dropped only after success; store lock never nested inside itself);
creation-marker delete; failure cases (single and mid-set) leave entries;
lock graph acyclic (service lock > store lock only); 64 tests green.

Looks good. Ship.
