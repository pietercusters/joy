---
phase: quick
plan: 260429-ciy
subsystem: ui
tags: [textual, rich-text, claude-status, indicators, tui]

requires:
  - phase: quick-260429-amk
    provides: "Claude agent status detection (is_claude, claude_state fields on TerminalSession)"
provides:
  - "Claude state indicators rendered in ProjectList rows (colored circles after project name)"
  - "Claude state indicators rendered in ProjectDetail terminal rows (robot icon + state circle)"
affects: [project-list, project-detail, terminal-pane]

tech-stack:
  added: []
  patterns:
    - "Compact indicator rendering in width-budgeted rows (subtract indicator_width from name_budget)"
    - "Claude state extraction from RelationshipIndex terminals (filter is_claude, map claude_state)"

key-files:
  created: []
  modified:
    - src/joy/widgets/project_list.py
    - src/joy/widgets/project_detail.py

key-decisions:
  - "Indicators rendered compact without spaces between circles for density"
  - "ProjectDetail uses plain-text labels with Unicode circles (ObjectRow does not support Rich styles)"
  - "Reuse INDICATOR_BUSY/WAITING/WAITING_INPUT constants from terminal_pane.py"

patterns-established:
  - "Claude state indicators: green filled circle = busy, yellow filled circle = waiting_input, dim hollow circle = idle/None"

requirements-completed: []

duration: 3min
completed: 2026-04-29
---

# Quick 260429-ciy: Show Claude Status Indicators in Project List and Detail

**Colored circle indicators (green/yellow/dim) for Claude agent states rendered inline in ProjectList rows and ProjectDetail terminal rows**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-29T07:04:23Z
- **Completed:** 2026-04-29T07:08:05Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- ProjectList rows show compact colored circle indicators after project name for each Claude session (green = busy, yellow = waiting_input, dim hollow = idle)
- ProjectDetail terminal rows show robot icon and state indicator for Claude sessions, plain name for non-Claude sessions
- Width budget accounting preserves row alignment in ProjectList when indicators are present

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Claude state indicators to ProjectList rows** - `2fb90ed` (feat)
2. **Task 2: Add Claude state indicators to ProjectDetail terminal rows** - `d823ecb` (feat)

## Files Created/Modified
- `src/joy/widgets/project_list.py` - Added claude_states parameter to build_content/set_counts, render colored circles after project name, extract states in update_badges
- `src/joy/widgets/project_detail.py` - Enriched Claude terminal session labels with robot icon and state indicator in _build_virtual_rows

## Decisions Made
- Indicators rendered compact (no spaces between circles) for visual density in the constrained project list width
- Used Unicode circle characters (same constants as terminal_pane.py) for consistency across all panes
- ProjectDetail labels use plain text with indicator characters since ObjectRow renders labels as plain Static content (no Rich styling available for colors in this context)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in test_terminal_load_on_mount (timing-sensitive async test) confirmed unrelated to changes

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Claude status indicators now visible across all project views
- Terminal pane already had indicators from the 260429-amk task; now ProjectList and ProjectDetail are consistent

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: quick-260429-ciy*
*Completed: 2026-04-29*
