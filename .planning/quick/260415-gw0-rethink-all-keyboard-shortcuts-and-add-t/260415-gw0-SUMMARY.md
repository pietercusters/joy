---
phase: 260415-gw0
plan: 01
subsystem: tui-keyboard
tags: [keyboard, shortcuts, hints, ux]
key-files:
  modified:
    - src/joy/app.py
    - src/joy/widgets/project_list.py
    - src/joy/widgets/terminal_pane.py
    - src/joy/widgets/worktree_pane.py
    - src/joy/widgets/object_row.py
    - tests/test_tui.py
decisions:
  - "n binding moved from JoyApp (global) to ProjectList (scoped) to prevent firing from TerminalPane/WorktreePane"
  - "o binding added as show=False alias for Enter in WorktreePane and TerminalPane for consistency"
  - "KIND_SHORTCUT dict placed in object_row.py as single source of truth for kind-to-key mapping"
  - "[key] hints rendered inline (dim grey) rather than in a separate widget for simplicity"
metrics:
  completed: 2026-04-15
---

# Quick Task 260415-gw0: Keyboard Shortcuts Rework Summary

Scoped n binding to ProjectList, added o as open alias in all panes, and added inline [key] global shortcut hints on every row.

## What Was Built

### Bug Fixes

1. **n scope fix**: Removed `Binding("n", "new_project", "New", priority=True)` from `JoyApp.BINDINGS`. Added `Binding("n", "new_project", "New")` to `ProjectList.BINDINGS` with a delegating `action_new_project` method. Now `n` only creates a project when the project list has focus.

2. **o opens in every pane**: Added `Binding("o", "activate_row", "Open", show=False)` to `WorktreePane.BINDINGS` and `Binding("o", "focus_session", "Open", show=False)` to `TerminalPane.BINDINGS`. The `o` key now works as an alias for Enter in all four panes.

3. **Bug 2 (e:rename_session)**: No action needed -- this binding and method did not exist in the codebase. Already clean.

### New Feature: Global Key Hints on Rows

Each row in every pane now shows the global shortcut key in brackets (dimmed) on the right side, telling the user which key jumps to or opens this item from any pane.

- **ObjectRow** (`object_row.py`): Added `KIND_SHORTCUT` dict mapping PresetKind to shortcut letter. Added 4th column `col-shortcut` (width 5, right-aligned, $text-muted) showing `[b]`, `[m]`, `[i]`, `[y]`, `[u]`, `[t]`, `[h]` per kind. Kinds without shortcuts (FILE, URL, REPO) show empty.

- **WorktreeRow** (`worktree_pane.py`): Appended `  [i]` with `style="dim"` to end of line 1 in `build_content()`, both for default-branch and non-default-branch code paths.

- **SessionRow** (`terminal_pane.py`): Appended `  [h]` with `style="dim"` at the end of `_build_content()` after the cwd.

### Tests

- `test_n_does_not_fire_from_terminal_pane`: Focuses TerminalPane, presses n, verifies no modal opens and project count unchanged.
- `test_o_opens_in_worktree_pane`: Verifies WorktreePane has an `o` binding mapped to `activate_row`.
- `test_o_opens_in_terminal_pane`: Verifies TerminalPane has an `o` binding mapped to `focus_session`.

All existing tests continue to pass (325 non-slow, 32/33 slow -- 1 pre-existing flaky test unrelated to changes).

## Commits

| Commit | Message |
|--------|---------|
| 3bb7ad9 | fix: keyboard shortcuts fixup -- n scope, add o to all panes, add global key hints on rows |

## Deviations from Plan

### Skipped Items

**1. Bug 2 (e:rename_session removal)** -- The `rename_session` binding and action method do not exist in the codebase. No `_PANE_HINTS` dictionary exists either. These were already clean; no changes needed.

**2. _PANE_HINTS updates** -- No `_PANE_HINTS` dictionary exists in `app.py` or anywhere in the codebase. Skipped all references to updating it.

## Known Stubs

None -- all features are fully wired.

## Self-Check: PASSED
