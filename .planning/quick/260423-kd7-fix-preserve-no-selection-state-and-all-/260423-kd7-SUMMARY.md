---
status: complete
quick_id: 260423-kd7
description: "fix: preserve no-selection state and all cursor positions across refresh in all panes"
date: 2026-04-23
commits:
  - c355baa
  - 32824e5
---

# Quick Task 260423-kd7: Summary

## What Changed

All four panes had identical cursor restore logic that conflated "first-time population" (cursor=-1, no prior rows) with "cleared selection" (cursor=-1, had rows via `clear_selection()`). Both cases triggered `self._cursor = 0`, incorrectly jumping the cursor back after an intentional clear.

### Fix

Added `had_rows_before = len(self._rows) > 0` flag before DOM rebuild, then three-way branch:
- **First-time** (no prior rows, cursor=-1): auto-select index 0
- **Cleared selection** (had rows, cursor=-1): preserve -1
- **Identity lost** (had cursor, item removed): clamp to valid range

### Files Modified

- `src/joy/widgets/terminal_pane.py` — cursor restore in `set_sessions()`
- `src/joy/widgets/worktree_pane.py` — cursor restore in `set_worktrees()`
- `src/joy/widgets/project_list.py` — cursor restore in `_rebuild()`
- `src/joy/widgets/project_detail.py` — cursor restore in `_render_project()`
- `tests/test_cursor_restore.py` — 4 new tests for no-selection preservation
