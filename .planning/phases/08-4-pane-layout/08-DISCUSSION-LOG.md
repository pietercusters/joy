# Phase 8: 4-Pane Layout - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 08-4-pane-layout
**Areas discussed:** Grid layout technique, Focus cycling order, Stub pane content & focus indicator, Footer / sub_title behavior with 4 panes

---

## Grid Layout Technique

### Q: Which layout primitive should we use for the 2x2 grid?

| Option | Description | Selected |
|--------|-------------|----------|
| Textual Grid (CSS grid) | Use Textual's Grid container with `grid-size: 2 2`. Idiomatic, easy to style. | ✓ |
| Nested Horizontal/Vertical | Two Horizontals inside a Vertical. Matches existing Horizontal pattern but less idiomatic. | |
| Textual DockLayout | Dock panes to edges. Overkill for a uniform 2×2. | |

**User's choice:** Textual Grid (CSS grid)

### Q: How should the 2x2 proportions be set?

| Option | Description | Selected |
|--------|-------------|----------|
| Equal 50/50 rows and columns | All four panes equal size. Predictable, parity for stubs. | ✓ |
| 1fr/2fr columns, 50/50 rows | Preserve current column bias, split rows evenly. | |
| 1fr/2fr columns, 2fr/1fr rows | Keep column bias AND emphasize top row. | |

**User's choice:** Equal 50/50 rows and columns

---

## Focus Cycling Order

### Q: What Tab order should cycle through the four panes?

| Option | Description | Selected |
|--------|-------------|----------|
| Reading order (TL → TR → BL → BR) | Projects → detail → terminal → worktree. Matches visual scan. | ✓ |
| Column-major (TL → BL → TR → BR) | Left column then right column. Less intuitive for a grid. | |
| Clockwise (TL → TR → BR → BL) | Spatial cycle but reverses bottom row. | |

**User's choice:** Reading order (TL → TR → BL → BR)

### Q: Should Tab focus wrap around at the end?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, wrap | Tab on last pane → first; Shift+Tab on first → last. Standard TUI. | ✓ |
| No, stop at edges | Tab stops at boundaries. | |

**User's choice:** Yes, wrap

### Q: When focus enters a pane, what should be focused inside it?

| Option | Description | Selected |
|--------|-------------|----------|
| Pane's primary interactive child | ListView in projects, scrollable in detail. Zero-regression. | ✓ |
| Pane container itself | User presses Enter/Arrow to dive in. Adds a keypress per switch. | |

**User's choice:** Pane's primary interactive child

---

## Stub Pane Content & Focus Indicator

### Q: What should the terminal and worktree stub panes display in Phase 8?

| Option | Description | Selected |
|--------|-------------|----------|
| Title + centered 'coming soon' | Bordered pane, title, centered muted message. Informative, signals WIP. | ✓ |
| Title only in border, empty body | Clean but can look broken. | |
| Minimal placeholder widget class per pane | Define classes now for Phase 9/12 to extend. | (rolled into D-08 — class approach chosen separately below) |

**User's choice:** Title + centered 'coming soon'

### Q: How should the focused pane be visually distinguished?

| Option | Description | Selected |
|--------|-------------|----------|
| Bordered panes; focused pane gets accent-color border | Clear at a glance; works with colorblind palettes. | ✓ |
| Textual default focus ring only | Less visible with 4 competing panes. | |
| Highlight the focused pane's title/header | Subtle; uniform borders. | |

**User's choice:** Bordered panes; focused pane gets accent-color border

### Q: Should the stub panes have a pane class/widget now or just CSS containers?

| Option | Description | Selected |
|--------|-------------|----------|
| Define TerminalPane and WorktreePane widget classes now | Phase 9/12 will extend them — smaller diffs later. | ✓ |
| Just use Static widgets with id and border-title | Less code now, more rewrite later. | |

**User's choice:** Define TerminalPane and WorktreePane widget classes now

---

## Footer / Sub-title Behavior

### Q: How should the Header sub_title update with 4 panes?

| Option | Description | Selected |
|--------|-------------|----------|
| Extend current logic: one label per pane | Projects / Detail / Terminal / Worktrees. Preserves v1.0 pattern. | ✓ |
| Show pane name + version/context | More info but risks clutter. | |
| Leave sub_title as 'Projects' always | Decoupled from focus; loses context cue. | |

**User's choice:** Extend current logic: one label per pane

### Q: How should the Tab binding be surfaced to the user?

| Option | Description | Selected |
|--------|-------------|----------|
| Add Tab/Shift+Tab to global BINDINGS with Footer visibility | Discoverable. | |
| Rely on Textual's default Tab behavior, no Footer entry | Smallest change; universal convention. | ✓ |
| Add only Tab (hide Shift+Tab) | Balance between discoverability and minimalism. | |

**User's choice:** Rely on Textual's default Tab behavior, no Footer entry

### Q: Should pane-specific keybindings appear in the Footer only when that pane is focused?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current behavior: widget BINDINGS show when widget is focused | Idiomatic Textual; consistent with v1.0. | ✓ |
| Always show all pane keybindings in Footer | Discoverable but crowded with 4 panes. | |

**User's choice:** Keep current behavior: widget BINDINGS show when widget is focused

---

## Claude's Discretion

- Exact border / accent color choices (readable across dark and light terminals).
- Whether to extract CSS to a `.tcss` file or keep it inline on `JoyApp` (current convention is inline).
- Exact wording / dim styling of "coming soon".
- Widget base class for `TerminalPane`/`WorktreePane` (`Container`, `Static`, or `Widget`).
- Internal pane IDs for CSS (`#projects-pane`, `#detail-pane`, `#terminal-pane`, `#worktrees-pane` suggested).

## Deferred Ideas

- User-resizable splits (keyboard-driven tool; not needed)
- Terminal pane content → Phase 12
- Worktree pane content → Phase 9
- Background refresh → Phase 10
- Persisting last-focused pane across restarts — not required
- Per-pane keybindings cheatsheet overlay — default Footer is sufficient
