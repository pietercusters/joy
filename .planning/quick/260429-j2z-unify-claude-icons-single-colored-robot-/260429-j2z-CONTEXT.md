# Quick Task 260429-j2z: Unify Claude icons — Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Task Boundary

Replace the current two-element pattern (robot icon + separate circle indicator) with a single robot icon whose color encodes the Claude session state. Apply consistently across TerminalPane, ProjectList, and ProjectDetail.

</domain>

<decisions>
## Implementation Decisions

### Icon glyph
- Change from `\U000f1325` (nf-md-robot_industrial — factory arm) to `\U000f06a9` (nf-md-robot — classic robot face)
- This is the closest glyph to the Claude logo style

### Unified indicator pattern
- One robot icon per Claude session, colored by state
- No separate circle indicators (●/○) anywhere
- busy → green 󰚩, waiting_input → yellow 󰚩, idle → dim 󰚩
- White space between multiple robot icons in ProjectList

### Constants cleanup
- Remove `INDICATOR_BUSY`, `INDICATOR_WAITING`, `INDICATOR_WAITING_INPUT`
- Keep `ICON_CLAUDE` but change its codepoint to `\U000f06a9`

### Files to change
- `terminal_pane.py`: ICON_CLAUDE codepoint, remove INDICATOR_* constants, simplify _build_content to render colored robot only
- `project_list.py`: replace circle indicators with colored robot icons (with spaces between)
- `project_detail.py`: simplify label enrichment to use colored robot only (no circle appended)
- `legend.py`: reduce to 3 terminal entries (green robot=busy, yellow robot=needs input, dim robot=idle) plus terminal session icon

### Non-Claude terminals
- Unchanged — terminal icon, no robot, no status indicator

</decisions>
