---
phase: quick
plan: 260428-kxu
subsystem: ui/icons
tags: [icons, legend, mr-status]
dependency_graph:
  requires: []
  provides: [ICON_MR_MERGED]
  affects: [legend-modal, worktree-pane-legend]
tech_stack:
  added: []
  patterns: [icon-constants, legend-sections]
key_files:
  created: []
  modified:
    - src/joy/widgets/icons.py
    - src/joy/screens/legend.py
decisions:
  - "Merged entry placed before closed entry in legend (merged is more common)"
  - "Purple color chosen for merged icon to match GitLab/GitHub merged MR convention"
metrics:
  duration_seconds: 96
  completed: "2026-04-28T13:08:50Z"
  tasks_completed: 1
  tasks_total: 1
---

# Quick Task 260428-kxu: Add Purple Merged/Closed MR Icon and Update Legend Summary

Added ICON_MR_MERGED constant (U+EAC3 nf-cod-git_merge) to icon constants and split the legend's combined "MR closed / merged" entry into separate purple "MR merged" and dim "MR closed" entries in both project MR and worktree pane sections.

## Task Results

| Task | Name | Commit | Status | Files |
|------|------|--------|--------|-------|
| 1 | Add ICON_MR_MERGED and update legend entries | 845ea9c | Done | src/joy/widgets/icons.py, src/joy/screens/legend.py |

## Changes Made

### icons.py
- Added `ICON_MR_MERGED = "\ueac3"` (nf-cod-git_merge) after ICON_MR_CLOSED, maintaining column alignment with existing constants.

### legend.py
- Added ICON_MR_MERGED to the import statement.
- Replaced single `"MR closed / merged"` entry in `_PROJECT_MR` with two entries: purple `"MR merged"` and dim `"MR closed"`.
- Added purple `"MR merged"` entry to `_WORKTREE_ICONS` after the MR draft entry.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- ICON_MR_MERGED imports correctly with expected codepoint U+EAC3.
- `_PROJECT_MR` has separate "MR merged" (purple) and "MR closed" (dim) entries.
- `_WORKTREE_ICONS` includes "MR merged" (purple) entry.
- Test suite: 358 passed, 1 pre-existing failure (test_terminal_load_on_mount, unrelated).
