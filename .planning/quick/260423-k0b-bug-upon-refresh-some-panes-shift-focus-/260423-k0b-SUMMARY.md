---
phase: quick
plan: 260423-k0b
subsystem: widgets
tags: [bugfix, cursor-restore, tui, tdd]
dependency_graph:
  requires: []
  provides: [cursor-identity-restore]
  affects: [project_list, project_detail]
tech_stack:
  added: []
  patterns: [save-restore-cursor-identity]
key_files:
  created:
    - tests/test_cursor_restore.py
  modified:
    - src/joy/widgets/project_list.py
    - src/joy/widgets/project_detail.py
decisions:
  - "Used (kind, value) tuple as identity key for ProjectDetail (matches ObjectItem natural key)"
  - "Used project.name as identity key for ProjectList (unique within project list)"
  - "initial_cursor parameter still takes precedence over saved identity (delete handler path)"
metrics:
  duration: "3m 35s"
  completed: "2026-04-23T12:31:37Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Quick 260423-k0b: Fix Cursor Reset on Pane Refresh Summary

Cursor identity save/restore for ProjectList and ProjectDetail using same pattern as TerminalPane/WorktreePane -- saves name or (kind, value) before DOM rebuild and restores by match after.

## What Changed

### Task 1: ProjectList._rebuild() cursor preservation
- Before `scroll.remove_children()`, saves the highlighted project's `name` and cursor index
- After rebuilding rows, restores cursor by matching `project.name`; falls back to clamped index if the project was removed
- First-time renders (cursor=-1, no prior selection) still start at index 0

### Task 2: ProjectDetail._render_project() cursor preservation
- Before `scroll.remove_children()`, saves the highlighted object's `(kind, value)` tuple and cursor index
- Only saves identity when `initial_cursor is None` (when initial_cursor is explicitly provided by delete handlers, that takes precedence)
- After rebuilding rows, restores cursor by matching `(kind, value)`; falls back to clamped index if the object was removed
- First-time renders still start at index 0

## TDD Gate Compliance

All tasks followed RED/GREEN TDD cycle:
1. `d00481f` - test(quick-260423-k0b): RED - failing tests for ProjectList cursor restore
2. `c98e247` - fix(quick-260423-k0b): GREEN - implement ProjectList cursor restore
3. `7914060` - test(quick-260423-k0b): RED - failing tests for ProjectDetail cursor restore
4. `ddcbcab` - fix(quick-260423-k0b): GREEN - implement ProjectDetail cursor restore

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 (RED) | d00481f | test(quick-260423-k0b): add failing tests for ProjectList cursor restore |
| 1 (GREEN) | c98e247 | fix(quick-260423-k0b): preserve ProjectList cursor across refresh/rebuild |
| 2 (RED) | 7914060 | test(quick-260423-k0b): add failing tests for ProjectDetail cursor restore |
| 2 (GREEN) | ddcbcab | fix(quick-260423-k0b): preserve ProjectDetail cursor across refresh/rebuild |

## Deviations from Plan

None - plan executed exactly as written.

## Test Results

- 7/7 new cursor restore tests pass
- 319 existing tests pass (excluding pre-existing known failures in test_propagation.py and test_sync.py documented in STATE.md)
- No regressions introduced

## Self-Check: PASSED

All 3 key files confirmed present. All 4 commit hashes verified in git log.
