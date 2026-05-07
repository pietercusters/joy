---
phase: quick
plan: 260428-gka
subsystem: tests
tags: [tech-debt, test-cleanup, terminal-matching]
dependency_graph:
  requires: []
  provides: [green-test-suite]
  affects: [tests/test_propagation.py, tests/test_sync.py]
tech_stack:
  added: []
  patterns: [tab_id-based-terminal-matching]
key_files:
  created: []
  modified:
    - tests/test_propagation.py
    - tests/test_sync.py
decisions:
  - Replaced TerminalSession type hint with bare `list` in _PropContext since sessions param is unused by remaining tests
metrics:
  duration: 238s
  completed: "2026-04-28T09:59:00Z"
  tasks_completed: 2
  tasks_total: 2
---

# Quick Task 260428-gka: Remove Tech Debt (10 Failing Tests) Summary

Deleted 6 obsolete tests referencing removed _propagate_terminal_auto_remove method and fixed 4 sync tests to use tab_id-based terminal matching instead of TERMINALS-name matching.

## Task Results

| Task | Name | Commit | Files | Status |
|------|------|--------|-------|--------|
| 1 | Delete obsolete TestTerminalAutoRemove | 2ef0f1c | tests/test_propagation.py | Done |
| 2 | Update 4 sync tests to tab_id matching | 5cc7ef9 | tests/test_sync.py | Done |

## Changes Made

### Task 1: Delete obsolete TestTerminalAutoRemove from test_propagation.py
- Deleted `TestTerminalAutoRemove` class (6 tests referencing non-existent `JoyApp._propagate_terminal_auto_remove`)
- Deleted `_sessions` helper function (only used by deleted class)
- Deleted `_get_propagate_terminal_remove` helper function
- Removed `TerminalSession` import (no longer needed)
- Updated module docstring to reflect MR auto-add only
- Result: 8 tests in TestMRAutoAdd pass, all dead code removed

### Task 2: Update 4 failing sync tests to use tab_id-based terminal matching
- Updated `_make_session` helper to accept `tab_id` parameter
- Updated `_make_project_with_worktree` helper to accept `iterm_tab_id` parameter
- Fixed SYNC-02 (test_sync_project_to_terminal): added `iterm_tab_id="tab1"` and `tab_id="tab1"`
- Fixed SYNC-04 (test_sync_worktree_to_terminal): added `iterm_tab_id="tab1"` and `tab_id="tab1"`
- Fixed SYNC-05 (test_sync_agent_to_project): added `iterm_tab_id="tab1"` and `tab_id="tab1"`
- Fixed SYNC-06 (test_sync_agent_to_worktree): added `iterm_tab_id="tab1"` and `tab_id="tab1"`
- Result: 12 passed, 1 deselected (slow SYNC-08)

## Verification

Full test suite: 355 passed, 1 failed (pre-existing), 36 deselected.

The single failure (`test_terminal_load_on_mount` in test_refresh.py) is pre-existing and unrelated to this change -- confirmed by running the test on the base commit before any modifications.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TerminalSession type hint in _PropContext**
- **Found during:** Task 1
- **Issue:** After removing the `TerminalSession` import, the `_PropContext.__init__` type hint `sessions: list[TerminalSession]` would cause a NameError
- **Fix:** Changed type hint to `sessions: list` (bare list) since no remaining tests pass sessions
- **Files modified:** tests/test_propagation.py
- **Commit:** 2ef0f1c

## Known Stubs

None.

## Pre-existing Issues

- `test_refresh.py::test_terminal_load_on_mount` fails on base commit (AssertionError: Expected at least 1 SessionRow after mount, got 0). Not related to this plan.
