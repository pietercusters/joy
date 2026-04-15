# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## cross-pane-sync-broken — Phase 16 merge removed compute_relationships() call, breaking all cross-pane sync
- **Date:** 2026-04-15
- **Error patterns:** cross-pane sync, _rel_index None, sync silently fails, panes don't follow, cursor not syncing, highlighted event ignored
- **Root cause:** Phase 16 commit rewrote _maybe_compute_relationships() and removed the compute_relationships() call that populated self._rel_index. Since _rel_index stayed None forever, all sync handlers short-circuited at their `_rel_index is not None` guard.
- **Fix:** Restored compute_relationships() call and its import inside _maybe_compute_relationships()
- **Files changed:** src/joy/app.py
---
