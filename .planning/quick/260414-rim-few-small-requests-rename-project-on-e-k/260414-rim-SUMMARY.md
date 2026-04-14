---
quick: 260414-rim
title: "Few small requests: rename on e, 1-space indent, default branch display, branch filter editor"
completed: 2026-04-14
duration: "8m 14s"
tasks_completed: 4
tasks_total: 4
key-files:
  modified:
    - src/joy/widgets/project_list.py
    - src/joy/screens/name_input.py
    - src/joy/models.py
    - src/joy/worktrees.py
    - src/joy/widgets/worktree_pane.py
    - src/joy/screens/settings.py
    - tests/test_worktrees.py
    - tests/test_screens.py
decisions:
  - "NameInputModal made generic with title/initial_value/placeholder/hint params for reuse"
  - "_do_save now includes branch_filter and refresh_interval, fixing latent bug where save reverted these to defaults"
---

# Quick Task 260414-rim: Few Small Requests Summary

Four independent UI improvements: rename project on e-key, 1-space project list indent, dim default branches in worktrees, editable branch filter in Settings.

## Task Results

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Rename project on 'e' key | 1286b7c | ProjectList binding + action, NameInputModal parameterized |
| 2 | 1-space indent in Project list | 0f79293 | ProjectRow adds leading space to name text |
| 3 | Default branches dim grey | 0d6f644 | WorktreeInfo.is_default_branch, mark-not-skip in discover, dim rendering |
| 4 | Branch filter editor in Settings | 04f9c72 | _BranchFilterWidget, _do_save includes branch_filter + refresh_interval |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Settings _do_save missing branch_filter and refresh_interval**
- **Found during:** Task 4
- **Issue:** _do_save constructed Config() without branch_filter or refresh_interval, reverting them to defaults on every save
- **Fix:** Added both fields to Config() constructor call in _do_save
- **Files modified:** src/joy/screens/settings.py

**2. [Rule 3 - Blocking] Test Tab count mismatch after adding focusable widget**
- **Found during:** Task 4
- **Issue:** Two tests (test_settings_save_returns_config, test_settings_save_still_returns_config_with_repos) used 6 Tab presses to reach Save button; new _BranchFilterWidget added one more focusable stop
- **Fix:** Updated both tests from 6 to 7 Tab presses
- **Files modified:** tests/test_screens.py

## Verification

All 284 tests pass (8 deselected slow TUI tests):
```
uv run pytest tests/ -x -q --ignore=tests/test_tui.py
284 passed, 8 deselected, 1 warning in 32.74s
```

## Self-Check: PASSED

All 8 modified files exist. All 4 task commits verified in git log.
