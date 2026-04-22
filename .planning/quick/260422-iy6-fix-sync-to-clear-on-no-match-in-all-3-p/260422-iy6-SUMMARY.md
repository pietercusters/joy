---
phase: quick-260422-iy6
plan: 01
subsystem: widgets/sync
tags: [bugfix, cross-pane-sync, stale-highlight]
dependency_graph:
  requires: []
  provides: ["sync_to-no-match-clear"]
  affects: ["project_list", "worktree_pane", "terminal_pane"]
tech_stack:
  added: []
  patterns: ["_cursor = -1 on no-match in sync_to()"]
key_files:
  created: []
  modified:
    - src/joy/widgets/project_list.py
    - src/joy/widgets/worktree_pane.py
    - src/joy/widgets/terminal_pane.py
    - tests/test_sync.py
decisions:
  - "Clear selection (_cursor = -1 + remove --highlight) instead of leaving stale cursor on sync_to() no-match"
metrics:
  duration: "3m 55s"
  completed: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
---

# Quick Task 260422-iy6: Fix sync_to() Clear on No-Match Summary

Clear _cursor to -1 and remove --highlight CSS class in all 3 pane sync_to() methods when no matching row is found, preventing stale highlight from misleading keyboard actions like 'i' (open IDE).

## Completed Tasks

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Fix sync_to() no-match path in all 3 pane widgets | be3527c | project_list.py, worktree_pane.py, terminal_pane.py: replace no-op comment with _cursor=-1 + remove_class("--highlight") |
| 2 | Add and update tests for no-match clear behavior | 9616762 | test_sync.py: update 3 Fake pane classes, update 4 existing assertions, add 4 new test functions (SYNC-10..13) |

## Changes Made

### Task 1: Widget sync_to() Fix

In all three panes (`ProjectList`, `WorktreePane`, `TerminalPane`), the `sync_to()` method previously left `_cursor` unchanged when no row matched ("D-08" behavior). This caused stale highlights: selecting a project with no related worktree would leave the previous worktree highlighted, so pressing 'i' would open the wrong IDE instance.

The fix replaces the no-op fallthrough after the for-loop with:
```python
self._cursor = -1
for r in self._rows:
    r.remove_class("--highlight")
```

This integrates with the existing `_cursor < 0` guard in `app.py`'s `action_open_ide()`, which already returns early when cursor is negative.

### Task 2: Test Updates

- Updated 3 `Fake*Pane.sync_to()` stubs to mirror the new clear behavior
- Changed 4 existing no-match assertions from `== 0` (unchanged) to `== -1` (cleared) in SYNC-01, SYNC-02, SYNC-03, SYNC-05
- Added 4 new dedicated tests:
  - SYNC-10: no-match clears WorktreePane from valid cursor
  - SYNC-11: no-match clears TerminalPane from valid cursor
  - SYNC-12: no-match clears ProjectList from valid cursor
  - SYNC-13: no-match from various starting positions clears all 3 pane types

## Deviations from Plan

None - plan executed exactly as written.

## Pre-existing Test Failures (Out of Scope)

The following tests were already failing before this change (confirmed via git stash verification):
- `test_sync_project_to_terminal` (SYNC-02): `compute_relationships` returns empty terminals_for() with PresetKind.TERMINALS objects
- `test_sync_worktree_to_terminal` (SYNC-04): same resolver issue
- `test_sync_agent_to_project` (SYNC-05 happy path): `project_for_terminal` returns None
- `test_sync_agent_to_worktree` (SYNC-06): same resolver issue
- `test_propagation.py::TestTerminalAutoRemove`: missing `_propagate_terminal_auto_remove` on JoyApp
- `test_refresh.py::test_terminal_load_on_mount`: pre-existing assertion failure

These are resolver/propagation issues unrelated to the sync_to() clear fix.

## Verification

- 334 tests pass (excluding 7 pre-existing failures)
- SYNC-07 (source inspection) passes: confirms sync_to() still contains no .focus() calls
- All 4 new SYNC-10..13 tests pass

## Known Stubs

None.

## Self-Check: PASSED
