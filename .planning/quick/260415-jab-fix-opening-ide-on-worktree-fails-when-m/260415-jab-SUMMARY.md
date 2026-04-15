---
phase: quick
plan: 260415-jab
subsystem: app
tags: [keybinding, ide, worktree, subprocess]
dependency_graph:
  requires: []
  provides: [action_open_ide, i-binding]
  affects: [app.py]
tech_stack:
  added: []
  patterns: [work(thread=True) for subprocess calls]
key_files:
  created: []
  modified:
    - src/joy/app.py
decisions:
  - "'i' binding added at app level (priority=True) so it fires regardless of focused pane"
  - "Defaults to 'Cursor' IDE when config.ide is empty or falsy"
  - "Returns early silently when project/rel_index/worktrees not ready — no error toasts"
metrics:
  duration: "~3 minutes"
  completed: "2026-04-15"
---

# Quick Task 260415-jab Summary

**One-liner:** Global 'i' keybinding in JoyApp opens IDE on first detected worktree via subprocess, restoring IDE access when a worktree row has an MR present.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add 'i' -> open IDE binding to JoyApp | 0b12320 | src/joy/app.py |

## What Was Done

Added three changes to `src/joy/app.py`:

1. `import subprocess` at the top of the file (was missing)
2. `Binding("i", "open_ide", "Open IDE", priority=True)` appended to `BINDINGS`
3. `action_open_ide` method decorated with `@work(thread=True)`:
   - Retrieves active project from `ProjectDetail._project`
   - Gets IDE from `self._config.ide` (falls back to `"Cursor"`)
   - Calls `self._rel_index.worktrees_for(project)` to find worktrees
   - Opens first worktree path: `subprocess.run(["open", "-a", ide, wt.path], check=False)`
   - Returns early silently if project/rel_index/worktrees are not yet available

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- 325 tests passed (39 deselected as slow/TUI), 0 failures
- No regressions introduced

## Self-Check: PASSED

- `src/joy/app.py` modified with all three required changes
- Commit `0b12320` exists and contains the changes
- All tests pass
