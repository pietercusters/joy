---
title: Sync-panes clear-on-no-match
date: 2026-04-22
context: Explored during /gsd-explore on feature/sync-panes-v2 branch
---

## Bug

When navigating to a project in ProjectList that has no related worktree or terminal session,
WorktreePane and TerminalPane still show their previously-highlighted item. The same problem
exists in all directions: navigating in WorktreePane or TerminalPane to an item with no related
counterpart leaves the other panes stale.

This breaks the `i` key (open IDE): it opens the stale highlighted worktree rather than the
one that belongs to the selected project.

## Root cause

All three `sync_to()` methods — in `project_list.py`, `worktree_pane.py`, and `terminal_pane.py`
— have an explicit "no match → leave cursor unchanged" fallback:

```python
# Example from worktree_pane.py ~line 427
for i, row in enumerate(self._rows):
    if row.repo_name == repo_name and row.branch == branch:
        ...
        return
# No match: _cursor and --highlight are untouched  ← the bug
```

## Desired behavior

The 3 panes (ProjectList, WorktreePane, TerminalPane) must always reflect a consistent
selection. When navigating to an item with no related counterpart in another pane, that pane
must clear its selection entirely — no row highlighted, `_cursor = -1`.

ProjectDetail is excluded: it receives updates via `set_project()` which already handles null.

## Fix approach

In each `sync_to()` method, replace the "no match → return silently" path with
"no match → clear selection":

```python
# After the loop, if no match found:
self._cursor = -1
for r in self._rows:
    r.remove_class("--highlight")
```

### Why this fixes `i` automatically

`action_open_ide` (app.py:783) already guards on `_cursor < 0`:
```python
if pane._cursor < 0 or not pane._rows or pane._cursor >= len(pane._rows):
    self.notify("No worktree selected", markup=False)
    return
```
Clearing to -1 triggers this guard naturally — no additional changes needed.

### `h` key is unaffected

`action_open_terminal` reads from `ProjectDetail._project`, not from `TerminalPane._cursor`.
It always acts on the selected project, which is the correct behavior.

## Files to change

- `src/joy/widgets/project_list.py` — `sync_to()` method
- `src/joy/widgets/worktree_pane.py` — `sync_to()` method
- `src/joy/widgets/terminal_pane.py` — `sync_to()` method

Tests to update/add: `tests/test_sync.py` — cases for "no match → clear" in all 3 directions.
