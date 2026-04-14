# Phase 2: TUI Shell - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-10
**Phase:** 02-tui-shell
**Mode:** discuss
**Areas analyzed:** Object display format, Pane navigation model, Footer key hints, Visual style & layout

## Assumptions Presented / Questions Asked

### Object display format

| Question | Options Presented | Answer |
|----------|-------------------|--------|
| How much info per object row? | Icon + label only / Icon + label + value (truncated) / Icon + label + type badge | Icon + label + value (truncated) |
| How to group multiple objects of same type? | Flat list in display order / Grouped by preset type / You decide | Grouped by preset type |
| How to handle long values? | Truncate to fit available width / Show domain only for URLs / You decide | Truncate to fit available width |

### Pane navigation model

| Question | Options Presented | Answer |
|----------|-------------------|--------|
| How does focus move left → right pane? | Tab key / Right arrow at edge / Enter selects AND focuses detail | Enter selects project AND focuses detail |
| Can user navigate objects in detail pane with j/k? | Yes / No (display-only) / You decide | Yes — j/k navigates objects in detail pane |
| How does user return to project list? | Escape / Tab cycles back / Both Escape and Tab | Escape returns to project list |

### Footer key hints

| Question | Options Presented | Answer |
|----------|-------------------|--------|
| How much to show in footer? | Minimal (3-4 keys) / Comprehensive (all bindings) / You decide | Comprehensive — all available bindings |
| Show pane context label? | Yes — pane name at left / No — just hints / You decide | Yes — show pane name at left of footer |

### Visual style & layout

| Question | Options Presented | Answer |
|----------|-------------------|--------|
| Left pane width? | Narrow sidebar ~25% / Balanced ~33% / Fixed character width | Balanced — ~33% width |
| Selection highlight style? | Full-row background / Cursor marker + dimmed / You decide | Full-row background highlight |
| Color scheme? | Textual default dark / Custom minimal dark / You decide | Textual default dark theme |

## Corrections Made

No corrections — all choices were direct selections from presented options.

## Deferred Ideas

None surfaced during discussion.
