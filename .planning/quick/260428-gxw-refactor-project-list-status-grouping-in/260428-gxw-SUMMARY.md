---
phase: quick-260428-gxw
plan: 01
subsystem: widgets/project_list
tags: [refactor, ui, grouping]
dependency_graph:
  requires: []
  provides: [status-grouped-project-list, inline-repo-name]
  affects: [project_list.py, test_project_list.py]
tech_stack:
  added: []
  patterns: [status-based-grouping, inline-metadata-display]
key_files:
  created: []
  modified:
    - src/joy/widgets/project_list.py
    - tests/test_project_list.py
decisions:
  - Status grouping order: Active (prio), Blocked (hold), Idle (idle)
  - Repo name rendered dim with trailing space before icon ribbon
  - Toggle status triggers full rebuild via set_projects for correct re-sort
metrics:
  duration: 157s
  completed: 2026-04-28
---

# Quick Task 260428-gxw: Refactor Project List Status Grouping Summary

Status-based project grouping (Active/Blocked/Idle) replaces repo-based grouping, with inline dim repo name between MR strip and icon ribbon.

## What Changed

### Task 1: Status grouping and inline repo name (92c0ce0)

- Replaced repo-based grouping logic in `_rebuild()` with status-based grouping using `STATUS_ORDER` list: Active (prio), Blocked (hold), Idle (idle)
- Each status bucket sorts projects alphabetically by name
- Empty status groups are skipped entirely
- Added `repo_name: str | None = None` parameter to `build_content()` rendering the repo name dim between MR strip and icon ribbon
- Updated `__init__` and `set_counts` to pass `repo_name=project.repo`
- Replaced `action_toggle_status` single-row re-render with `set_projects()` call for full rebuild and correct re-sort
- Updated all docstrings and comments from "repo grouping" to "status grouping"

### Task 2: Tests for repo name display (534eb55)

- Added `test_project_row_shows_repo_name_when_set`: verifies repo name appears with dim style
- Added `test_project_row_hides_repo_name_when_none`: verifies no extra text when repo is None
- Added `test_project_row_constructor_passes_repo`: verifies constructor wires repo through to content
- Updated `_make_project` helper to accept `repo: str | None = None` parameter
- All 9 tests pass (6 existing + 3 new)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED
