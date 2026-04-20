---
phase: quick-260420-ket
plan: 01
subsystem: cross-pane-sync
tags: [refactor, pane-sync, worktree-pane, terminal-pane, app]
dependency_graph:
  requires: [quick-260420-izh]
  provides: [clear_selection-api, no-dimmed-concept]
  affects: [WorktreePane, TerminalPane, JoyApp._sync_from_*]
tech_stack:
  added: []
  patterns: [clear_selection-over-dimmed-state]
key_files:
  modified:
    - src/joy/widgets/worktree_pane.py
    - src/joy/widgets/terminal_pane.py
    - src/joy/app.py
decisions:
  - "clear_selection() (cursor=-1, remove --highlight) is the correct empty state — no special dimmed mode needed"
  - "Pre-existing cursor<0 guard in action_open_ide handles no-selection case without _is_dimmed check"
metrics:
  duration: ~5 minutes
  completed: 2026-04-20
  tasks_completed: 3
  files_modified: 3
---

# Phase quick-260420-ket Plan 01: Remove Dimmed Selection — clear_selection() on No-Match Summary

**One-liner:** Remove dimmed-selection visual mode entirely; unlinked panes show cursor=-1 (no selection) instead of a greyed-out highlighted row.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove dimmed API from WorktreePane and TerminalPane, add clear_selection() | f1343b5 | worktree_pane.py, terminal_pane.py |
| 2 | Update app.py — replace set_dimmed() calls with clear_selection(), remove _is_dimmed guard | 70b6db1 | app.py |
| 3 | Verify zero residue and run tests | (no commit needed) | — |

## What Was Done

Removed the dimmed-selection concept introduced in quick-260420-izh from all three files:

**WorktreePane (worktree_pane.py):**
- Removed two `--dim-selection` CSS blocks from DEFAULT_CSS
- Removed `self._is_dimmed: bool = False` from `__init__`
- Replaced `set_dimmed()` method with `clear_selection()` (cursor=-1, loop remove --highlight)
- Removed `_is_dimmed` toast guard from `action_activate_row`

**TerminalPane (terminal_pane.py):**
- Removed two `--dim-selection` CSS blocks from DEFAULT_CSS
- Removed `self._is_dimmed: bool = False` from `__init__`
- Replaced `set_dimmed()` method with `clear_selection()` (cursor=-1, loop remove --highlight)
- Removed `_is_dimmed` toast guard from `action_focus_session`

**JoyApp (app.py):**
- `_sync_from_project`: replaced 4x `set_dimmed()` calls with `clear_selection()` on no-match paths
- `_sync_from_worktree`: removed `set_dimmed(False)`, replaced 3x `set_dimmed(True)` with `clear_selection()`; updated docstring
- `_sync_from_session`: removed `set_dimmed(False)`, replaced 3x `set_dimmed(True)` with `clear_selection()`; updated docstring
- `action_open_ide`: removed 3-line `_is_dimmed` guard block (existing `_cursor < 0` guard handles no-selection)

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- Zero `_is_dimmed`, `set_dimmed`, `--dim-selection` references in all `.py` source files
- `clear_selection()` defined in both `WorktreePane` (line 437) and `TerminalPane` (line 381)
- All three `_sync_from_*` methods use `clear_selection()` on no-match paths
- `action_open_ide` has no `_is_dimmed` check — only `_cursor < 0` guard remains
- 330+ fast tests pass; 5 pre-existing failures confirmed on base commit before changes

## Known Stubs

None.

## Threat Flags

None — pure internal refactor, no new trust boundaries or external surfaces.

## Self-Check: PASSED

- src/joy/widgets/worktree_pane.py: modified, committed in f1343b5
- src/joy/widgets/terminal_pane.py: modified, committed in f1343b5
- src/joy/app.py: modified, committed in 70b6db1
- Commits f1343b5 and 70b6db1 present in git log
