---
name: 260414-nrt Context
description: User decisions for Details pane redesign task
type: context
---

# Quick Task 260414-nrt: Details pane redesign — Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Task Boundary

Four UI improvements to the joy TUI:
1. Add repo field to the Details overview
2. Redesign Details view: 3-column layout (icon | value | kind), no headers, kind right-aligned, value wraps
3. Add 1 blank line of whitespace before every section header in all panes
4. Add a legend popup on `l` key that shows all icons and colored icons in all panes with their meaning

</domain>

<decisions>
## Implementation Decisions

### Legend popup style
- Modal overlay (centered over current pane)
- Dismissed with Escape or pressing `l` again

### Details column widths
- Icon column: fixed, ~3 chars wide
- Kind column: fixed, ~12 chars wide, right-aligned
- Value column: fills remaining space, wraps if content is too long

### Whitespace before headers
- 1 blank line before each section header (subtle separation)

### Claude's Discretion
- Exact Textual widget type for modal (Screen vs ModalScreen vs custom widget)
- Exact icons and their grouping/organization in the legend
- CSS implementation details for column layout

</decisions>

<specifics>
## Specific Ideas

- "label" column is dropped from Details view — only icon, value, kind remain
- Kind should appear right-aligned in its column
- Legend should be comprehensive — cover all icons from all panes (WorktreePane, ProjectsPane, Details)

</specifics>
