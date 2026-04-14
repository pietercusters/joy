---
phase: quick-260414-k2u
plan: 01
subsystem: worktree-pane
tags: [tui, cursor-navigation, worktree, mr-integration, keyboard-bindings]
dependency_graph:
  requires: []
  provides: [worktree-cursor-navigation, mrinfo-url-field]
  affects: [worktree-pane, mr-status, models]
tech_stack:
  added: []
  patterns: [cursor/_rows/--highlight pattern (mirrors TerminalPane), module-level imports for patchability]
key_files:
  created:
    - tests/test_worktree_pane_cursor.py
  modified:
    - src/joy/models.py
    - src/joy/mr_status.py
    - src/joy/widgets/worktree_pane.py
    - tests/test_worktree_pane.py
decisions:
  - Move webbrowser/subprocess to module-level imports in worktree_pane.py to enable unit test patching
  - Update test_pane_read_only -> test_pane_interactive to reflect BINDINGS addition
metrics:
  duration: ~12min
  completed: 2026-04-14
  tasks_completed: 3
  tasks_total: 3
  files_changed: 5
---

# Phase quick-260414-k2u Plan 01: WorktreePane cursor navigation and Enter activation

**One-liner:** j/k/enter/escape cursor navigation on WorktreePane with Enter opening MR URL or IDE via module-level webbrowser/subprocess.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add url field to MRInfo and populate in mr_status.py | 9fb7ca2 | src/joy/models.py, src/joy/mr_status.py |
| 2 | Add cursor navigation and Enter handler to WorktreePane | 51a6f7a | src/joy/widgets/worktree_pane.py, tests/test_worktree_pane.py |
| 3 | Write unit tests for cursor navigation and Enter actions | 49648c1 | tests/test_worktree_pane_cursor.py, src/joy/widgets/worktree_pane.py |

## What Was Built

**MRInfo.url field (Task 1):**
- Added `url: str = ""` as the last field of MRInfo dataclass — default preserves all existing call sites
- GitHub `gh pr list` now requests the `url` JSON field and stores it as `pr.get("url", "")`
- GitLab stores `mr.get("web_url", "")` as MRInfo.url

**WorktreePane cursor navigation (Task 2):**
- WorktreeRow now stores `repo_name`, `branch`, `path`, `mr_info` as instance attributes
- WorktreePane.BINDINGS added: escape/up/down/k/j/enter
- `_cursor: int = -1` and `_rows: list[WorktreeRow] = []` state in `__init__`
- `set_worktrees` initialises `_rows` with WorktreeRow instances, `_cursor = 0` if rows exist
- GroupHeader rows excluded from `_rows` (only WorktreeRow items tracked)
- `_update_highlight` removes/adds `--highlight` class and calls `scroll_visible()`
- `action_activate_row`: Enter on row with `mr_info.url` calls `webbrowser.open(url)`, else `subprocess.run(["open", "-a", ide, path])`
- `action_focus_projects` returns focus to `#project-list`
- CSS added: `WorktreeRow.--highlight` and focused variant

**Unit tests (Task 3):**
- 7 test cases in `tests/test_worktree_pane_cursor.py`
- Pure unit test for BINDINGS presence (no TUI)
- Async tests using `asyncio.run()` pattern matching existing TerminalPane tests
- Patch targets at module level (`joy.widgets.worktree_pane.webbrowser`, `joy.widgets.worktree_pane.subprocess`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved webbrowser/subprocess to module-level imports**
- **Found during:** Task 3 (RED phase)
- **Issue:** Inline imports inside `action_activate_row` meant `joy.widgets.worktree_pane.webbrowser` didn't exist as a patchable attribute; `patch()` raised `AttributeError`
- **Fix:** Moved `import subprocess` and `import webbrowser` to module-level in worktree_pane.py, removed inline imports
- **Files modified:** src/joy/widgets/worktree_pane.py
- **Commit:** 49648c1

**2. [Rule 1 - Bug] Updated test_pane_read_only to test_pane_interactive**
- **Found during:** Task 2
- **Issue:** Existing test `test_pane_read_only` asserted `WorktreePane.BINDINGS == []`, which would fail after adding BINDINGS in Task 2
- **Fix:** Renamed test and updated assertion to verify the new BINDINGS keys (j, k, enter, escape) are present
- **Files modified:** tests/test_worktree_pane.py
- **Commit:** 51a6f7a

## Test Results

- 7 new cursor tests: all pass
- Full fast suite: 282 passed, 38 deselected (slow/macos_integration)

## Self-Check

- src/joy/models.py — MRInfo.url field present
- src/joy/mr_status.py — GitHub url field requested and stored, GitLab web_url stored
- src/joy/widgets/worktree_pane.py — BINDINGS, _cursor/_rows, _update_highlight, action methods
- tests/test_worktree_pane_cursor.py — 7 test cases, all green
- Commits 9fb7ca2, 51a6f7a, 49648c1 all exist

## Self-Check: PASSED
