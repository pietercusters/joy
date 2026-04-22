---
title: Fix sync_to() to clear selection on no match in all 3 panes
date: 2026-04-22
priority: high
---

## Task

Fix the stale-highlight bug in pane synchronization. When `sync_to()` finds no matching row,
it must clear the selection instead of leaving the old highlight in place.

## Context

See note: `.planning/notes/sync-panes-clear-on-no-match.md`

## Changes required

### 1. `src/joy/widgets/project_list.py` — `sync_to()`

After the for-loop, if no match was found, add:
```python
self._cursor = -1
for r in self._rows:
    r.remove_class("--highlight")
```

### 2. `src/joy/widgets/worktree_pane.py` — `sync_to()`

Same pattern after the for-loop.

### 3. `src/joy/widgets/terminal_pane.py` — `sync_to()`

Same pattern after the for-loop.

### 4. `tests/test_sync.py` — add/update test cases

Add test cases covering:
- Project with no worktree → WorktreePane clears
- Project with no terminal → TerminalPane clears
- Worktree with no project → ProjectList clears, TerminalPane clears
- Session with no project → ProjectList clears, WorktreePane clears

## Acceptance criteria

- [ ] Selecting a project with no related worktree leaves WorktreePane with no highlight
- [ ] Selecting a project with no related terminal leaves TerminalPane with no highlight
- [ ] Same behavior in all 3 directions (worktree→others, terminal→others)
- [ ] `i` key shows "No worktree selected" notification when WorktreePane has no selection
- [ ] `h` key behavior unchanged (acts on selected project, not terminal pane cursor)
- [ ] All existing sync tests still pass
