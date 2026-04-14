---
phase: 13-project-workflow-settings-docs
plan: 02
subsystem: widgets
tags: [tui, project-list, grouping, cursor-navigation, refactor]

# Dependency graph
requires:
  - "13-01 (Project.repo field, JoyApp._repos init)"
provides:
  - "ProjectList with VerticalScroll + GroupHeader + cursor-based navigation"
  - "Project grouping by repo with 'Other' last"
  - "Filter mode compatible with grouped layout"
affects: [13-03, 13-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cursor/_rows/--highlight pattern replicated from TerminalPane/WorktreePane"
    - "Deferred render via call_after_refresh with generation counter for race prevention"
    - "is_attached guard to prevent MountError on early callback execution"

key-files:
  created: []
  modified:
    - src/joy/widgets/project_list.py
    - src/joy/app.py
    - src/joy/widgets/project_detail.py
    - src/joy/widgets/terminal_pane.py
    - tests/test_tui.py
    - tests/test_filter.py
    - tests/test_pane_layout.py

key-decisions:
  - "Duplicated GroupHeader widget per-file to avoid cross-widget coupling (same pattern as worktree_pane and terminal_pane)"
  - "Used is_attached guard with reschedule instead of async set_projects to handle early mount timing"

patterns-established:
  - "Non-focusable scroll containers (_ProjectScroll) prevent focus stealing"
  - "Generation counter pattern for deferred DOM rebuilds"

requirements-completed: [FLOW-01]

# Metrics
duration: 9min
completed: 2026-04-14
---

# Phase 13 Plan 02: ProjectList Refactor to VerticalScroll + GroupHeader + Cursor Navigation Summary

**Full rewrite of ProjectList from ListView to VerticalScroll/GroupHeader/cursor pattern with repo-based project grouping and filter mode compatibility**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-14T10:53:29Z
- **Completed:** 2026-04-14T11:02:08Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Replaced ListView-based ProjectList with VerticalScroll + GroupHeader + cursor navigation pattern
- Added ProjectRow (Static), GroupHeader (Static), _ProjectScroll (VerticalScroll, can_focus=False)
- Projects grouped by repo (alphabetical) with "Other" group last for unmatched projects
- Wired app.py to load repos via load_repos() and pass to ProjectList.set_projects
- Updated focus targets in project_detail.py and terminal_pane.py (#project-listview -> #project-list)
- Updated all test files to use new ProjectList API (no more ListView/ListItem references)
- All 305 tests pass (268 non-slow + 37 slow TUI/filter tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor ProjectList to VerticalScroll + GroupHeader + cursor navigation** - `1bf92c3`
2. **Task 2: Update filter mode and fix tests for refactored ProjectList** - `7345198`

## Files Created/Modified
- `src/joy/widgets/project_list.py` - Full rewrite: removed JoyListView/ListView, added _ProjectScroll, GroupHeader, ProjectRow, cursor-based ProjectList with repo grouping
- `src/joy/app.py` - Updated _load_data to load repos, _set_projects to accept/pass repos, removed JoyListView import, updated focus ID references
- `src/joy/widgets/project_detail.py` - Updated action_focus_list to focus #project-list directly
- `src/joy/widgets/terminal_pane.py` - Updated action_focus_projects to focus #project-list directly
- `tests/test_tui.py` - Removed project-listview references
- `tests/test_filter.py` - Replaced ListView/ListItem assertions with ProjectRow/_rows pattern
- `tests/test_pane_layout.py` - Removed project-listview references

## Decisions Made
- Duplicated GroupHeader widget definition (same CSS) to avoid cross-widget coupling, consistent with existing pattern in worktree_pane.py and terminal_pane.py
- Added is_attached guard in _rebuild to prevent MountError when callback fires before scroll container is fully mounted

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MountError on early _rebuild callback**
- **Found during:** Task 2 (test execution)
- **Issue:** _rebuild fired via call_after_refresh before _ProjectScroll was attached to the DOM, causing MountError when trying to mount children
- **Fix:** Added is_attached check with reschedule via call_after_refresh
- **Files modified:** src/joy/widgets/project_list.py
- **Commit:** 7345198

## Issues Encountered
None beyond the auto-fixed MountError.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ProjectList now uses the same cursor/_rows/--highlight pattern as all other panes
- Repo grouping is functional and ready for testing with real repo data
- Filter mode works with grouped layout, hiding empty group headers
- All tests pass with no regressions

## Self-Check: PASSED
