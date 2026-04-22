---
phase: quick-260422-ksh
plan: 01
subsystem: dispatch, project-detail, app
tags: [refactor, dispatch-table, virtual-rows, keystroke, repo-shortcut]
dependency_graph:
  requires: []
  provides: [dispatch.py, virtual-row-assembly, modular-dispatch, repo-keystroke, consistent-quick-open]
  affects: [src/joy/app.py, src/joy/widgets/project_detail.py, src/joy/widgets/object_row.py]
tech_stack:
  added: []
  patterns: [4-state-dispatch-table, virtual-row-sentinel, kind-value-resolver]
key_files:
  created:
    - src/joy/dispatch.py
  modified:
    - src/joy/widgets/project_detail.py
    - src/joy/widgets/object_row.py
    - src/joy/app.py
    - tests/test_refresh.py
decisions:
  - "TERMINALS dispatch: when value exists, calls _do_activate_tab() directly rather than _do_open_global() to preserve correct tab-ID based activation semantics"
  - "action_toggle_auto_refresh removed: binding was R (now used for refresh), method body removed since it was only accessible via the binding"
  - "resolver_worktrees param on set_project defaults to None (no change) vs [] (clear) to allow call sites without rel_index to leave prior resolver data intact"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-22T13:08:10Z"
  tasks_completed: 2
  files_modified: 5
  files_created: 1
---

# Quick Task 260422-ksh: Refactor ProjectDetail and Keystroke Dispatch Summary

**One-liner:** Table-driven KindConfig dispatch replacing scattered if/else, with TERMINALS/WORKTREE virtual rows in ProjectDetail and r=repo-copy / R=refresh key swap.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create dispatch.py and update virtual row assembly in ProjectDetail | 9279432 | src/joy/dispatch.py (new), src/joy/widgets/object_row.py, src/joy/widgets/project_detail.py |
| 2 | Wire dispatch table into app.py quick-open shortcuts and fix r/R key conflict | f4eff22 | src/joy/app.py, tests/test_refresh.py |

## What Was Built

### src/joy/dispatch.py (new)

`KindConfig` frozen dataclass with 4 boolean fields (`exists_openable`, `exists_not_openable`, `missing_auto_create`, `missing_needs_input`) plus `missing_notify` string. `DISPATCH` table maps all 10 `PresetKind` values to their `KindConfig`. Adding a new kind's behavior now requires only editing this file.

### ProjectDetail virtual row layer

`_build_virtual_rows(project)` assembles the `grouped` dict:
- Stored `project.objects` (as before)
- REPO row synthesized from `project.repo` (as before)
- TERMINALS row synthesized from `project.iterm_tab_id` (new)
- WORKTREE rows synthesized from `self._resolver_worktrees`, deduplicated against stored worktrees (new)

Virtual resolver WORKTREE rows are tracked in `self._readonly_items` (set of `id(item)`). Both `action_delete_object` and `action_force_delete_object` check this set and notify "Worktree rows are read-only" instead of deleting.

`set_project()` gained an optional `resolver_worktrees` parameter (default `None` = no change).

### app.py dispatch refactor

- `_open_first_of_kind()` now: looks up `DISPATCH[kind]`, calls `_resolve_kind_value()` to find value from all sources, then routes to `_copy_value_bg`, `_do_activate_tab`, `_do_open_global`, `_auto_create_kind`, or `_prompt_for_kind`.
- `_resolve_kind_value()`: checks `project.repo` for REPO, `project.iterm_tab_id` for TERMINALS, resolver index for WORKTREE, then falls through to `project.objects`.
- `_copy_value_bg()`: generic clipboard worker replacing `_copy_branch`.
- `_auto_create_kind()`: handles TERMINALS auto-create (was inline in `action_open_terminal`).
- `_prompt_for_kind()`: handles missing_needs_input kinds via `ValueInputModal`.
- `action_open_repo()`: new, triggers `_open_first_of_kind(REPO)`.
- `action_open_terminal()`: simplified to `_open_first_of_kind(TERMINALS)`.

### Key binding change: r ↔ R swap

| Key | Before | After |
|-----|--------|-------|
| `r` | `action_refresh_worktrees` (priority) | `action_open_repo` |
| `R` | `action_toggle_auto_refresh` (hidden) | `action_refresh_worktrees` (priority) |

`action_toggle_auto_refresh` method and binding removed entirely.

### Resolver worktrees wired at all call sites

All 6 `set_project()` call sites in app.py now pass `resolver_worktrees`:
- `on_project_list_project_highlighted`
- `on_project_list_project_selected`
- `_propagate_changes` (post-rebuild)
- `_sync_from_worktree`
- `_sync_from_session`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated 4 test_refresh.py tests after r→R key binding swap**
- **Found during:** Task 2 verification
- **Issue:** `test_refresh_failure_shows_stale`, `test_no_toast_on_manual_refresh`, `test_terminal_refresh_on_r_key`, `test_timestamp_updates_after_refresh` all pressed `r` to trigger manual refresh; after key swap `r` now triggers repo dispatch instead.
- **Fix:** Changed `pilot.press("r")` to `pilot.press("R")` in all 4 tests; updated docstrings accordingly.
- **Files modified:** tests/test_refresh.py
- **Commit:** f4eff22

## Pre-existing Failures (Out of Scope)

These failures existed before this task and were not introduced or fixed here:

| Test | Failure |
|------|---------|
| test_propagation.py::TestTerminalAutoRemove (6 tests) | `JoyApp._propagate_terminal_auto_remove` attribute does not exist |
| test_refresh.py::test_terminal_load_on_mount | `SessionRow` count assertion fails (iTerm2 unavailable in test env) |
| test_sync.py::test_sync_project_to_terminal | resolver `terminals_for()` returns empty for session-matched TERMINALS |
| test_sync.py::test_sync_worktree_to_terminal | same |
| test_sync.py::test_sync_agent_to_project | `project_for_terminal()` returns None |
| test_sync.py::test_sync_agent_to_worktree | same |

All 11 pre-existing failures confirmed by running against the commit before Task 1 changes.

## Test Results

- **342 tests pass** (fast suite, excluding test_tui.py)
- **11 pre-existing failures** (out of scope, not caused by this task)
- **0 new failures introduced**

## Self-Check: PASSED

- FOUND: src/joy/dispatch.py
- FOUND: src/joy/widgets/project_detail.py
- FOUND: src/joy/widgets/object_row.py
- FOUND: src/joy/app.py
- FOUND commit: 9279432
- FOUND commit: f4eff22
