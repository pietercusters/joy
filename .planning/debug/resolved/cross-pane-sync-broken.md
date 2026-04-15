---
status: resolved
trigger: "Cross-pane sync stopped working after phase 16 worktree merge accidentally reverted phase 15 source changes."
created: 2026-04-15T00:00:00Z
updated: 2026-04-15T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED — Phase 16 removed the compute_relationships() call from _maybe_compute_relationships, so _rel_index is never set, and all sync handlers short-circuit
test: N/A — root cause confirmed
expecting: N/A
next_action: Awaiting human verification that cross-pane sync works in the live TUI

## Symptoms

expected: When moving cursor in ProjectList, WorktreePane and TerminalPane cursor should follow (sync_to). When moving cursor in WorktreePane, ProjectList and TerminalPane should follow. When moving cursor in TerminalPane, ProjectList and WorktreePane should follow.
actual: Cross-pane sync does not work — panes no longer follow each other when navigating.
errors: No crash errors reported — sync just silently doesn't happen.
reproduction: Launch joy TUI, navigate between projects in left pane, other panes don't update cursor. Navigate in WorktreePane, ProjectList doesn't follow.
started: After phase 16 executor worktree ran (commit 949ad93). Files were restored from 949ad93^ parent but sync still broken.

## Eliminated

## Evidence

- timestamp: 2026-04-15T00:01:00Z
  checked: All occurrences of _rel_index in app.py
  found: _rel_index is initialized to None in __init__ (line 74) and NEVER assigned again. All 6 sync handler checks (lines 438, 465, 489) gate on `_rel_index is not None` — always False.
  implication: Every sync path is dead code; sync can never fire.

- timestamp: 2026-04-15T00:02:00Z
  checked: git show b58f44d:src/joy/app.py (last working phase 15 commit)
  found: Old _maybe_compute_relationships() imported compute_relationships from joy.resolver and assigned result to self._rel_index. Phase 16 commit 4cb9099 rewrote this method to call _propagate_changes() instead, removing the compute_relationships() call entirely.
  implication: Phase 16 inadvertently deleted the line that populates _rel_index, breaking all downstream sync.

- timestamp: 2026-04-15T00:03:00Z
  checked: src/joy/resolver.py still exists with compute_relationships() function
  found: Module is intact; RelationshipIndex class and compute_relationships function are fully present and functional.
  implication: Fix is simply to restore the compute_relationships() call inside _maybe_compute_relationships()

## Resolution

root_cause: Phase 16 commit 4cb9099 rewrote _maybe_compute_relationships() and removed the compute_relationships() call that populated self._rel_index. Since _rel_index stays None forever, all sync handlers (on_project_list_project_highlighted, on_worktree_pane_worktree_highlighted, on_terminal_pane_session_highlighted) short-circuit at their `_rel_index is not None` guard and never execute sync.
fix: Restore compute_relationships() call in _maybe_compute_relationships() and re-add the import
verification: Import OK, 325 tests pass (0 failures), syntax valid. Awaiting human verification of live TUI sync behavior.
files_changed: [src/joy/app.py]
