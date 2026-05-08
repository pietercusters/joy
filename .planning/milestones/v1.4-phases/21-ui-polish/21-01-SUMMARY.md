---
phase: 21-ui-polish
plan: 01
subsystem: ui
tags: [textual, css, focus, border, highlight]

# Dependency graph
requires:
  - phase: 20-widget-tests-snapshots
    provides: Layout tests (test_pane_layout.py) for verification
provides:
  - Self-contained DEFAULT_CSS in all 5 focusable panes (border, focus, focus-within, highlight, scoped spacer)
  - Removal of split CSS ownership between app.py and widget files
affects: [21-02-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [self-contained-widget-css, dual-focus-highlight, scoped-section-spacer]

key-files:
  created: []
  modified:
    - src/joy/widgets/project_list.py
    - src/joy/widgets/project_detail.py
    - src/joy/widgets/worktree_pane.py
    - src/joy/widgets/terminal_pane.py
    - src/joy/widgets/mr_pane.py
    - src/joy/app.py

key-decisions:
  - "Removed #project-list and #project-detail CSS from app.py in same commit as widget CSS addition (Rule 2 - split ownership elimination)"

patterns-established:
  - "Self-contained widget CSS: every focusable pane owns its border, :focus, :focus-within, row highlight, and scoped section-spacer in DEFAULT_CSS"
  - "Dual focus highlight: both :focus and :focus-within variants for row highlight ensures full-accent row when pane holds direct focus"
  - "Scoped section-spacer: always prefix .section-spacer with widget class name to prevent DOM-wide CSS leaks"

requirements-completed: [UIPOL-01, UIPOL-02]

# Metrics
duration: 2min
completed: 2026-05-08
---

# Phase 21 Plan 01: CSS Consistency Summary

**Self-contained border/focus/highlight CSS in all 5 focusable panes, eliminating split CSS ownership between app.py and widget DEFAULT_CSS**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-08T12:20:23Z
- **Completed:** 2026-05-08T12:22:59Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- All 5 widget DEFAULT_CSS blocks are self-contained with border, :focus, :focus-within, row highlight, and scoped section-spacer rules
- Removed duplicate #project-list and #project-detail CSS from app.py (no more split CSS ownership)
- All 9 visual CSS inconsistencies from the Phase 21 audit are resolved
- No unscoped .section-spacer rules remain in any widget file

## Task Commits

Each task was committed atomically:

1. **Task 1: Add self-contained border/focus CSS to ProjectList and ProjectDetail** - `2b516ba` (feat)
2. **Task 2: Add :focus row highlight variants to WorktreePane, TerminalPane, MRPane + scope MRPane spacer** - `f1831c9` (feat)

## Files Created/Modified
- `src/joy/widgets/project_list.py` - Added ProjectList border, :focus, :focus-within rules to DEFAULT_CSS
- `src/joy/widgets/project_detail.py` - Added border, :focus, :focus-within, :focus highlight, scoped section-spacer
- `src/joy/widgets/worktree_pane.py` - Added WorktreePane:focus WorktreeRow.--highlight rule
- `src/joy/widgets/terminal_pane.py` - Added TerminalPane:focus SessionRow.--highlight rule
- `src/joy/widgets/mr_pane.py` - Added MRPane:focus MRRow.--highlight + scoped MRPane .section-spacer
- `src/joy/app.py` - Removed duplicate #project-list and #project-detail border/focus CSS

## Decisions Made
- Removed app.py CSS for #project-list and #project-detail in the same commit as adding widget DEFAULT_CSS (avoids a window where both define borders, which would create specificity conflicts)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Removed duplicate CSS from app.py**
- **Found during:** Task 1
- **Issue:** Plan did not explicitly include removing the #project-list and #project-detail CSS from app.py, but leaving it would create duplicate conflicting border rules (app.py ID selectors vs widget DEFAULT_CSS type selectors)
- **Fix:** Stripped #project-list, #project-list:focus-within, #project-detail, #project-detail:focus-within rules from JoyApp.CSS, keeping only #pane-grid layout
- **Files modified:** src/joy/app.py
- **Verification:** Layout tests pass (9/9), no visual regressions
- **Committed in:** 2b516ba (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical)
**Impact on plan:** Essential for correctness -- without removing app.py CSS, duplicate border rules would conflict. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 panes now follow the canonical CSS pattern, ready for Plan 02 (snapshot baseline updates)
- Layout tests pass, confirming no regressions

---
*Phase: 21-ui-polish*
*Completed: 2026-05-08*
