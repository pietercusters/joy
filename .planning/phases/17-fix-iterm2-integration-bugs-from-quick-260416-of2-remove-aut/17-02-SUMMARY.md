---
phase: 17-fix-iterm2-integration-bugs
plan: 02
subsystem: ui, terminal
tags: [iterm2, textual, tab-close, archive, modal]

# Dependency graph
requires:
  - phase: 17-01
    provides: close_tab function in terminal_sessions.py
provides:
  - No auto-sync tab creation in refresh cycles or new project creation
  - h-key creates iTerm2 tab when none linked (with in-flight guard)
  - Stale tab heal notifies user to press h to relink
  - _close_tab_bg worker for tab-level close
  - Delete and archive both close iTerm2 tab before removing project
  - ArchiveModal removed, replaced by ConfirmationModal
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_close_tab_bg mirrors _close_sessions_bg: @work decorator, lazy import, silent-fail"
    - "ConfirmationModal reused for archive (hint kwarg customizes footer text)"

key-files:
  created: []
  modified:
    - src/joy/app.py
    - src/joy/widgets/project_list.py
    - src/joy/screens/__init__.py
  deleted:
    - src/joy/screens/archive_modal.py

key-decisions:
  - "Always close tab on archive (no choice offered) -- simplifies UX, ArchiveModal removed"
  - "Tab creation moved from auto-sync to explicit h-key press -- user controls when tabs are created"
  - "Stale-heal notifies user instead of silently auto-recreating tabs"

patterns-established:
  - "Tab-close on project removal: check iterm_tab_id, call _close_tab_bg before list mutation"
  - "ConfirmationModal with custom hint kwarg for action-specific confirmation text"

requirements-completed: [FIX17-REMOVE-AUTO-SYNC, FIX17-TAB-CLOSE-ON-DELETE-ARCHIVE]

# Metrics
duration: 4min
completed: 2026-04-16
---

# Phase 17 Plan 02: Remove Auto-Sync and Add Tab-Close on Delete/Archive Summary

**Removed automatic iTerm2 tab creation from refresh/new-project, moved tab creation to h-key, added tab-close on delete/archive, replaced ArchiveModal with ConfirmationModal**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-16T18:16:07Z
- **Completed:** 2026-04-16T18:19:46Z
- **Tasks:** 2
- **Files modified:** 3 modified, 1 deleted

## Accomplishments
- Removed all auto-sync tab creation from _set_terminal_sessions and action_new_project (D-01, D-02, D-05, D-06)
- h-key now creates iTerm2 tab when none linked, with _tabs_creating guard preventing duplicates (D-03, D-04)
- Stale tab heal notifies user with "press h to relink" message instead of silently auto-recreating
- Delete and archive both close entire iTerm2 tab before removing project from list (D-09, D-10, D-12)
- ArchiveModal and ArchiveChoice deleted, replaced by ConfirmationModal with custom hint
- All 304 non-pre-existing tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Modify app.py -- remove auto-sync, add _close_tab_bg, fix action_open_terminal** - `663e7c2` (feat)
2. **Task 2: Modify project_list.py delete/archive + remove ArchiveModal + clean screens/__init__** - `49a651c` (feat)

## Files Created/Modified
- `src/joy/app.py` - Removed auto-create branch from _set_terminal_sessions, removed auto-create from action_new_project, modified action_open_terminal to create tab on h-key, added _close_tab_bg worker
- `src/joy/widgets/project_list.py` - Added _close_tab_bg call to action_delete_project, replaced ArchiveModal with ConfirmationModal in action_archive_project
- `src/joy/screens/__init__.py` - Removed ArchiveChoice and ArchiveModal exports
- `src/joy/screens/archive_modal.py` - Deleted (replaced by ConfirmationModal)

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Pre-existing Test Failures

The following test failures exist on the base commit (pre-existing, not caused by this plan):
- `test_propagation.py::TestTerminalAutoRemove` (6 tests) - references non-existent `JoyApp._propagate_terminal_auto_remove`
- `test_sync.py` (4 tests) - resolver's terminals_for() returns empty list / sync agent tests
- `test_refresh.py::test_terminal_load_on_mount` - iTerm2 connection test (environment-dependent)

These are out-of-scope for this plan and were verified as pre-existing by Plan 01.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All iTerm2 integration bugs from quick-260416-of2 code review are now fixed
- Auto-sync removed, tab-close on delete/archive implemented, ArchiveModal simplified
- Phase 17 is complete

## Self-Check: PASSED

All files exist, all commits verified, deleted file confirmed removed, all content checks passed.

---
*Phase: 17-fix-iterm2-integration-bugs*
*Completed: 2026-04-16*
