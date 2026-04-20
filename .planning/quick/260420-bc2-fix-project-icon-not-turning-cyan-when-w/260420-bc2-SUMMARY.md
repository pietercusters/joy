---
phase: quick-260420-bc2
plan: "01"
subsystem: project-list
tags: [icon-ribbon, presence-signals, live-counts, tdd]
dependency_graph:
  requires: []
  provides: [live-wt-icon-cyan, live-terminal-icon-cyan]
  affects: [ProjectRow.build_content, ProjectRow.set_counts, ProjectList.action_toggle_status]
tech_stack:
  added: []
  patterns: [effective_has-override-pattern]
key_files:
  created: []
  modified:
    - src/joy/widgets/project_list.py
    - tests/test_project_list.py
decisions:
  - "Use effective_has dict override inside build_content so live counts never modify stored has state"
  - "Store _wt_count/_agent_count on ProjectRow instance so action_toggle_status re-renders preserve last counts"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-20T06:15:19Z"
  tasks_completed: 1
  files_modified: 2
---

# Phase quick-260420-bc2 Plan 01: Fix Project Icon Cyan Coloring Summary

**One-liner:** Fix worktree and terminal icon coloring to turn cyan from live wt_count/agent_count, not only from stored project objects.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Add failing tests for icon coloring from live counts | e96b29b | tests/test_project_list.py |
| GREEN | Fix icon coloring to use live wt_count/agent_count | f58be3e | src/joy/widgets/project_list.py |

## What Was Built

The project list icon ribbon previously only turned the worktree (folder) and terminal icons cyan when a project had stored `PresetKind.WORKTREE` or `PresetKind.TERMINALS` objects. Live active worktrees and terminals from the RelationshipIndex were ignored.

**Fix:**

1. `build_content()` gains `wt_count: int = 0` and `agent_count: int = 0` parameters.
2. An `effective_has` dict is computed by copying `has` and overriding `"worktree"` and `"terminal"` entries when the respective live count is > 0. The ribbon uses `effective_has` instead of `has`.
3. `set_counts()` stores `wt_count` and `agent_count` as `_wt_count`/`_agent_count` on the instance and passes them into `build_content`.
4. `ProjectRow.__init__` initializes `_wt_count = 0` and `_agent_count = 0`.
5. `action_toggle_status` re-render now passes `row._wt_count` and `row._agent_count` so status-cycle re-renders preserve live icon state.

## Test Coverage

5 new tests added (Tests A–E per plan spec):

- **A:** no WORKTREE object + wt_count=0 → grey50 dim
- **B:** no WORKTREE object + wt_count=1 → cyan
- **C:** stored WORKTREE + wt_count=0 → cyan (stored object still counts)
- **D:** no TERMINALS + agent_count=0 → grey50 dim
- **E:** no TERMINALS + agent_count=1 → cyan

All 6 tests in test_project_list.py pass.

## Deviations from Plan

None — plan executed exactly as written.

## Pre-existing Failures

11 tests in test_propagation.py, test_refresh.py, and test_sync.py were already failing before this task. Verified by stashing changes and running tests against base commit. These are out of scope for this plan.

## TDD Gate Compliance

- RED gate: commit e96b29b — `test(quick-260420-bc2): add failing tests for icon coloring from live wt/agent counts`
- GREEN gate: commit f58be3e — `feat(quick-260420-bc2): fix icon coloring to use live wt_count/agent_count`

## Self-Check: PASSED

- [x] `src/joy/widgets/project_list.py` modified — confirmed present
- [x] `tests/test_project_list.py` modified — confirmed present
- [x] RED commit e96b29b — confirmed in git log
- [x] GREEN commit f58be3e — confirmed in git log
- [x] All 6 tests pass
