---
phase: 17-fix-iterm2-integration-bugs
plan: 01
subsystem: testing, terminal
tags: [pytest, monkeypatch, iterm2, fixture, isolation]

# Dependency graph
requires: []
provides:
  - Autouse session-scoped fixture isolating all tests from ~/.joy/ filesystem
  - close_tab(tab_id) function for closing iTerm2 tabs by tab_id
affects: [17-02-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Session-scoped monkeypatch for module-level constant isolation"
    - "close_tab mirrors close_session pattern: lazy import, nonlocal success, silent fail"

key-files:
  created: []
  modified:
    - tests/conftest.py
    - src/joy/terminal_sessions.py

key-decisions:
  - "Session-scoped fixture (not function-scoped) to avoid per-test overhead while still isolating the entire session"
  - "close_tab iterates terminal_windows->tabs (same as fetch_sessions) rather than using a hypothetical get_tab_by_id"

patterns-established:
  - "Autouse session fixture for store path isolation: all store constants patched to tmp dir"
  - "Tab-level iTerm2 operations follow same lazy-import + Connection().run_until_complete pattern as session-level"

requirements-completed: [FIX17-TEST-ISOLATION, FIX17-CLOSE-TAB]

# Metrics
duration: 21min
completed: 2026-04-16
---

# Phase 17 Plan 01: Test Isolation and close_tab Foundation Summary

**Autouse pytest fixture isolating all tests from ~/.joy/ paths, plus close_tab iTerm2 function for tab-level close**

## Performance

- **Duration:** 21 min
- **Started:** 2026-04-16T17:43:22Z
- **Completed:** 2026-04-16T18:04:52Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Session-scoped autouse fixture patches JOY_DIR, PROJECTS_PATH, CONFIG_PATH, REPOS_PATH, ARCHIVE_PATH to tmp directory -- no test can touch real ~/.joy/
- close_tab(tab_id, force) function added to terminal_sessions.py following identical lazy-import + silent-fail pattern as close_session
- All 293 non-TUI tests pass without modification

## Task Commits

Each task was committed atomically:

1. **Task 1: Add autouse store-path isolation fixture to conftest.py** - `67a5a3c` (feat)
2. **Task 2: Add close_tab function to terminal_sessions.py** - `ce23e1a` (feat)

## Files Created/Modified
- `tests/conftest.py` - Added _isolated_store_paths autouse session fixture patching all 5 store path constants
- `src/joy/terminal_sessions.py` - Added close_tab function after close_session (lines 225-254)

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Pre-existing Test Failures

The following test failures exist on the base commit (pre-existing, not caused by this plan):
- `test_sync.py::test_sync_project_to_terminal` - resolver's terminals_for() returns empty list
- `test_sync.py::test_sync_worktree_to_terminal` - same resolver issue
- `test_propagation.py::TestTerminalAutoRemove` - references non-existent `JoyApp._propagate_terminal_auto_remove`
- `test_refresh.py::test_terminal_load_on_mount` - iTerm2 connection test (environment-dependent)

These are out-of-scope for this plan and were verified as pre-existing by testing on the base commit.

## Issues Encountered
- pytest-timeout not installed, so `--timeout=30` flag from plan verification command was skipped (not needed -- tests complete quickly)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- close_tab function ready for Plan 02 to use in delete/archive tab cleanup
- Store path isolation active for all future test runs
- Plan 02 can proceed without blockers

## Self-Check: PASSED

All files exist, all commits verified, all content checks passed.

---
*Phase: 17-fix-iterm2-integration-bugs*
*Completed: 2026-04-16*
