---
phase: 08-4-pane-layout
plan: 01
subsystem: ui
tags: [textual, widget, tui, grid-layout, tdd]

# Dependency graph
requires:
  - phase: 05-settings-search-distribution
    provides: "Complete v1.0 app with 2-pane layout, all keybindings, modals"
provides:
  - "TerminalPane stub widget (focusable, border_title='Terminal', 'coming soon')"
  - "WorktreePane stub widget (focusable, border_title='Worktrees', 'coming soon')"
  - "joy.widgets exports for TerminalPane and WorktreePane"
  - "9 failing tests defining 4-pane grid layout and Tab focus cycling contract"
affects: [08-02-PLAN, phase-09-worktree-pane, phase-12-terminal-pane]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Stub pane widget pattern: Widget subclass with can_focus=True, border_title, centered Static, empty BINDINGS"]

key-files:
  created:
    - src/joy/widgets/terminal_pane.py
    - src/joy/widgets/worktree_pane.py
    - tests/test_pane_layout.py
  modified:
    - src/joy/widgets/__init__.py

key-decisions:
  - "Stub panes subclass Widget with can_focus=True, matching existing ProjectDetail pattern"
  - "DEFAULT_CSS uses accent border on :focus and :focus-within for visual consistency (D-11, D-12)"
  - "Tests written as RED phase — describe target behavior for Plan 02 to implement"

patterns-established:
  - "Stub pane widget: Widget(can_focus=True) + border_title + centered Static('coming soon') + empty BINDINGS"
  - "Focus accent border via DEFAULT_CSS :focus/:focus-within pseudo-classes"

requirements-completed: [PANE-01]

# Metrics
duration: 2min
completed: 2026-04-13
---

# Phase 8 Plan 01: Stub Pane Widgets and Failing Layout Tests Summary

**TerminalPane and WorktreePane stub widgets with 9 RED-phase tests defining the 4-pane grid layout and Tab focus cycling contract**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-13T08:18:41Z
- **Completed:** 2026-04-13T08:21:17Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created TerminalPane and WorktreePane as focusable stub widgets with border titles, centered muted "coming soon" text, accent-on-focus CSS, and empty BINDINGS
- Updated joy.widgets __init__.py to export both new widget classes
- Wrote 9 failing tests covering PANE-01 (4-pane grid), PANE-02 (Tab cycling), D-13 (sub_title per pane), and regression (project list nav, Enter/Escape)
- Verified all 188 existing tests remain green

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TerminalPane and WorktreePane stub widgets** - `111a134` (feat)
2. **Task 2: Write failing tests for 4-pane grid layout and Tab focus cycling** - `c493f24` (test)

## Files Created/Modified
- `src/joy/widgets/terminal_pane.py` - TerminalPane stub widget with border_title "Terminal"
- `src/joy/widgets/worktree_pane.py` - WorktreePane stub widget with border_title "Worktrees"
- `src/joy/widgets/__init__.py` - Updated to export TerminalPane and WorktreePane
- `tests/test_pane_layout.py` - 9 failing tests for 4-pane grid layout contract (RED phase)

## Decisions Made
- Followed plan as specified — stub widgets use Widget(can_focus=True) pattern matching existing ProjectDetail
- DEFAULT_CSS applies accent border on :focus and :focus-within for uniform visual indicator (D-11, D-12)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

| File | Line | Stub | Reason |
|------|------|------|--------|
| src/joy/widgets/terminal_pane.py | 40 | Static("coming soon") | Intentional placeholder per D-09; Phase 12 will fill in terminal content |
| src/joy/widgets/worktree_pane.py | 40 | Static("coming soon") | Intentional placeholder per D-09; Phase 9 will fill in worktree content |

These stubs are intentional by design (D-08, D-09) and do not block the plan's goal of establishing widget contracts and test expectations.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- TerminalPane and WorktreePane are ready for Plan 02 to wire into app.py's Grid layout
- 9 failing tests define the exact contract Plan 02 must satisfy (GREEN phase)
- All 188 existing tests pass — no regressions

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 08-4-pane-layout*
*Completed: 2026-04-13*
