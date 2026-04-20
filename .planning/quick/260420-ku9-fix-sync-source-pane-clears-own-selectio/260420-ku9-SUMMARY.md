---
phase: quick-260420-ku9
plan: "01"
subsystem: cross-pane-sync
tags: [bug-fix, sync, pane-selection]
dependency_graph:
  requires: []
  provides: [SYNC-SOURCE-PANE-BUG]
  affects: [app.py, _sync_from_worktree, _sync_from_session]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - src/joy/app.py
decisions:
  - "Source pane in sync handler must never clear its own selection — only the other pane is cleared"
metrics:
  duration: "~3 minutes"
  completed: "2026-04-20T13:03:28Z"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase quick-260420-ku9 Plan 01: Fix sync source pane clears own selection — Summary

**One-liner:** Removed self-clearing calls from both sync else-branches so navigating to an unlinked item keeps the source pane's own selection intact.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove source-pane self-clear from both sync else branches | 6cb32a2 | src/joy/app.py |

## What Was Built

Two targeted line removals in `src/joy/app.py`:

- `_sync_from_worktree` else branch: removed `wt_pane.clear_selection()` (the source pane call), updated comment to "clear other panes". Only `term_pane.clear_selection()` remains.
- `_sync_from_session` else branch: removed `term_pane.clear_selection()` (the source pane call), updated comment to "clear other panes". Only `wt_pane.clear_selection()` remains.

## Verification

- Automated check: PASS — neither source pane clears itself in its own sync else branch
- Test suite: 338 passed (pre-existing failures in TestTerminalAutoRemove and test_sync/test_refresh are unrelated to this change and existed on the base commit)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- src/joy/app.py modified: confirmed
- Commit 6cb32a2 exists: confirmed
- No unexpected file deletions
