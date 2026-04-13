---
phase: 11-mr-ci-status
plan: 02
subsystem: ui-integration
tags: [worktree-pane, mr-status, ci-badges, textual, rich-text, tdd]

# Dependency graph
requires:
  - phase: 11-mr-ci-status
    plan: 01
    provides: MRInfo dataclass, fetch_mr_data function
  - phase: 09-worktree-pane
    provides: WorktreeRow, WorktreePane, build_content, set_worktrees
  - phase: 10-background-refresh-engine
    provides: _load_worktrees worker, set_refresh_label, border_title pattern
provides:
  - Extended WorktreeRow with MR badge rendering (line 1 MR number, open/draft icon, CI icon)
  - Context-sensitive line 2 (author + commit when MR, path when no MR)
  - set_worktrees mr_data parameter for MRInfo routing to rows
  - set_refresh_label mr_error parameter for border_title MR failure warning
  - fetch_mr_data wired into app.py background worker
affects: [11-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Context-sensitive two-line row: line 2 switches between path and MR metadata based on mr_info presence"
    - "Icon constants for MR state: ICON_MR_OPEN (green), ICON_MR_DRAFT (dim), ICON_CI_PASS/FAIL/PENDING"
    - "CI pending uses distinct codepoint (U+F192) from ICON_DIRTY (U+F111) to avoid visual confusion"
    - "Optional parameter propagation: mr_data flows app -> pane -> row via keyword arguments with None defaults"

key-files:
  created: []
  modified:
    - src/joy/widgets/worktree_pane.py
    - src/joy/app.py
    - tests/test_worktree_pane.py

key-decisions:
  - "Added fetch_mr_data mock to all JoyApp test fixtures to prevent real CLI calls during tests"
  - "MR badges render between branch name and dirty/upstream indicators on line 1 (per D-02)"
  - "Total MR failure detection: repos with known forge + worktrees exist + zero MR data returned"

patterns-established:
  - "Test fixtures for JoyApp must mock joy.mr_status.fetch_mr_data alongside discover_worktrees"

requirements-completed: [WKTR-07, WKTR-08, WKTR-09]

# Metrics
duration: 9min
completed: 2026-04-13
---

# Phase 11 Plan 02: MR Row Rendering & App Integration Summary

**Extended WorktreeRow with MR/CI badges on line 1 and author+commit on line 2, wired fetch_mr_data into app.py background worker, with 14 new TDD tests**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-13T13:35:28Z
- **Completed:** 2026-04-13T13:44:23Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- 5 new Nerd Font icon constants: ICON_MR_OPEN, ICON_MR_DRAFT, ICON_CI_PASS, ICON_CI_FAIL, ICON_CI_PENDING
- build_content extended with mr_info parameter: MR number (!N), open/draft icon, CI status icon on line 1
- Line 2 context-sensitive: @author + commit hash/msg when MR present, abbreviated path when not (D-01)
- set_worktrees accepts mr_data dict, routes MRInfo to matching WorktreeRow by (repo_name, branch) key
- set_refresh_label accepts mr_error flag, shows warning in border_title on total MR fetch failure (D-10)
- app.py _load_worktrees calls fetch_mr_data after discover_worktrees in same background thread (D-06)
- app.py _set_worktrees and _update_refresh_label forward MR data and error state to pane
- 14 new TDD tests covering all MR rendering variants, icon display, line 2 switching, constructor, pane wiring
- All 268 tests pass (full regression suite green)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED -- Failing tests for MR row rendering** - `792b349` (test)
2. **Task 2: GREEN -- Implement MR rendering and app integration** - `c7fd4ac` (feat)

## Files Created/Modified

- `src/joy/widgets/worktree_pane.py` - Added 5 MR/CI icon constants, extended build_content/WorktreeRow.__init__ with mr_info, extended set_worktrees with mr_data, extended set_refresh_label with mr_error
- `src/joy/app.py` - Added _mr_fetch_failed state, extended _load_worktrees with fetch_mr_data call, extended _set_worktrees with mr_data/mr_failed params, extended _update_refresh_label with mr_error passthrough
- `tests/test_worktree_pane.py` - Added 14 new tests, _sample_mr_info helper, fetch_mr_data mock to JoyApp fixtures

## Decisions Made

- Added `fetch_mr_data` mock (returning empty dict) to all three JoyApp test fixtures (mock_store_with_worktrees, mock_store_empty_repos, mock_store_repos_no_worktrees) -- required because _load_worktrees now imports and calls fetch_mr_data, which would attempt real CLI calls without mocking
- Used distinct codepoint U+F192 (dot-circle-o) for CI pending instead of U+F111 (same as ICON_DIRTY) per RESEARCH.md recommendation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added fetch_mr_data mock to existing test fixtures**
- **Found during:** Task 2
- **Issue:** Existing JoyApp integration tests (test_loading_placeholder, test_app_loads_worktrees, etc.) failed because _load_worktrees now imports fetch_mr_data which tries to run real gh/glab CLI commands
- **Fix:** Added `patch("joy.mr_status.fetch_mr_data", return_value={})` to all three JoyApp test fixtures
- **Files modified:** tests/test_worktree_pane.py
- **Commit:** c7fd4ac

## Issues Encountered
None beyond the fixture mock addition.

## User Setup Required
None -- no external service configuration required.

## Next Phase Readiness
- WorktreeRow now renders full MR/CI information when MRInfo is provided
- app.py fetches and passes MR data through the refresh pipeline
- Plan 11-03 (keybinding integration or additional features) can build on this foundation
- All tests green, no blockers

## Self-Check: PASSED

All files verified present on disk. All commit hashes found in git log.

---
*Phase: 11-mr-ci-status*
*Completed: 2026-04-13*
