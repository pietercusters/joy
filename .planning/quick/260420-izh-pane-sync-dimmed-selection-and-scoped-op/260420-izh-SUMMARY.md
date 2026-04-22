---
phase: quick-260420-izh
plan: 01
subsystem: widgets/sync
tags: [sync, dimmed-state, ux, cross-pane]
dependency_graph:
  requires: []
  provides: [dimmed-selection-state, bool-sync-returns, scoped-open-guards]
  affects: [worktree_pane, terminal_pane, project_list, app-sync-methods]
tech_stack:
  added: []
  patterns: [_is_dimmed flag, set_dimmed() method, CSS class toggle, bool return on sync_to]
key_files:
  created: []
  modified:
    - src/joy/widgets/worktree_pane.py
    - src/joy/widgets/terminal_pane.py
    - src/joy/widgets/project_list.py
    - src/joy/app.py
decisions:
  - "Dimmed state is managed via CSS class --dim-selection on the pane widget, not on individual rows — matches existing --highlight pattern and avoids per-row state"
  - "set_dimmed() is safe inside _is_syncing=True block because it only adds/removes a CSS class with no message posting"
  - "Pre-existing test failures (11 tests in test_sync.py, test_propagation.py, test_refresh.py) confirmed pre-existing on base branch — not introduced by this plan"
metrics:
  duration_minutes: ~15
  completed_date: "2026-04-20"
  tasks_completed: 2
  files_modified: 4
---

# Phase quick-260420-izh Plan 01: Pane Sync Dimmed Selection and Scoped Open Summary

**One-liner:** Cross-pane sync now returns bool and drives a `--dim-selection` CSS class on WorktreePane/TerminalPane when no item matches the active project, with toast guards on open actions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add bool returns and dimmed state to WorktreePane, TerminalPane, ProjectList | c933e9d | worktree_pane.py, terminal_pane.py, project_list.py |
| 2 | Update app.py sync methods to read bool returns and set dimmed state | fe6f0d8 | app.py |

## What Was Built

### Task 1 — Widget changes (3 files)

**WorktreePane (`worktree_pane.py`):**
- `_is_dimmed: bool = False` added to `__init__`
- `sync_to()` return type changed `None` → `bool` (returns `True` on match, `False` on no match)
- `set_dimmed(dimmed: bool)` method added — adds/removes `--dim-selection` CSS class
- `action_activate_row()` now guards on `_is_dimmed` first, shows `"No worktree for this project"` toast and returns early
- CSS rule added: `WorktreePane.--dim-selection WorktreeRow.--highlight { background: transparent; color: $text-muted; text-style: dim; }`

**TerminalPane (`terminal_pane.py`):**
- `_is_dimmed: bool = False` added to `__init__`
- `sync_to()` return type changed `None` → `bool` (returns `True` on match, `False` on no match)
- `set_dimmed(dimmed: bool)` method added — adds/removes `--dim-selection` CSS class
- `action_focus_session()` now guards on `_is_dimmed` first, shows `"No terminal for this project"` toast and returns early
- CSS rule added: `TerminalPane.--dim-selection SessionRow.--highlight { background: transparent; color: $text-muted; text-style: dim; }`

**ProjectList (`project_list.py`):**
- `sync_to()` return type changed `None` → `bool` for uniform pattern (no dimmed state needed on project list)

### Task 2 — App sync methods (`app.py`)

**`_sync_from_project()`:** Now reads `sync_to()` bool return and calls `set_dimmed()` on both panes. When no worktrees/terminals exist for the project, calls `set_dimmed(True)` directly.

**`_sync_from_worktree()`:** Now reads `sync_to()` bool return on TerminalPane and calls `set_dimmed()`. When worktree is unlinked to any project, dims TerminalPane.

**`_sync_from_session()`:** Now reads `sync_to()` bool return on WorktreePane and calls `set_dimmed()`. When session is unlinked to any project, dims WorktreePane.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all dimmed state logic is wired end-to-end.

## Threat Flags

None — changes are entirely internal TUI state management with no new network endpoints, auth paths, or external I/O.

## Pre-existing Test Failures (out of scope)

11 tests were failing on the base branch before this plan and remain failing after:
- `tests/test_propagation.py::TestTerminalAutoRemove` (6 tests) — `JoyApp._propagate_terminal_auto_remove` missing
- `tests/test_sync.py` (4 tests) — resolver `terminals_for` / `project_for_terminal` not matching test data
- `tests/test_refresh.py::test_terminal_load_on_mount` (1 test) — pre-existing

These are out-of-scope per deviation scope boundary rules. Logged here for awareness.

## Self-Check: PASSED

- `src/joy/widgets/worktree_pane.py` — FOUND (modified)
- `src/joy/widgets/terminal_pane.py` — FOUND (modified)
- `src/joy/widgets/project_list.py` — FOUND (modified)
- `src/joy/app.py` — FOUND (modified)
- Commit `c933e9d` — FOUND in git log
- Commit `fe6f0d8` — FOUND in git log
