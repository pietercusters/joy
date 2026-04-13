# Phase 8: 4-Pane Layout - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the existing 2-pane horizontal layout (ProjectList + ProjectDetail) into a 2×2 grid with four panes: projects (top-left), details (top-right), terminal placeholder (bottom-left), worktree placeholder (bottom-right). Tab cycles focus across all four. All v1.0 functionality — project list navigation, detail pane rendering, keyboard bindings, modals — must continue to work identically.

Out of scope: filling in the terminal pane (Phase 12) or the worktree pane (Phase 9). Background refresh (Phase 10) and user-resizable splits are not part of this phase.

</domain>

<decisions>
## Implementation Decisions

### Grid Layout
- **D-01:** Use Textual's `Grid` container with CSS `grid-size: 2 2` for the top-level layout. Idiomatic Textual, clean separation of layout from logic, easy to style via the existing CSS string on `JoyApp`.
- **D-02:** Equal 50/50 proportions on both rows and columns. All four panes get the same area. Predictable, keeps stubs on visual parity with the real panes, and avoids having to rework column widths in Phase 9/12 when those panes gain content.
- **D-03:** Replace the current `Horizontal(ProjectList, ProjectDetail)` in `JoyApp.compose()` (`src/joy/app.py:39-45`) with a `Grid` that yields four children in TL→TR→BL→BR order.

### Focus Cycling
- **D-04:** Tab order follows reading order: Projects (TL) → Detail (TR) → Terminal (BL) → Worktrees (BR). Shift+Tab reverses the same sequence. This matches how users visually scan the grid.
- **D-05:** Focus wraps around. Tab on the last pane returns to the first; Shift+Tab on the first pane goes to the last. Consistent with Textual's default focus behavior.
- **D-06:** When focus enters a pane, it lands on the pane's primary interactive child — not on the outer container. Projects pane focuses its `ListView`, detail pane focuses its scrollable content, stub panes focus their container (since they have no interactive children yet). This preserves zero-regression behavior for v1.0 flows where arrow keys work the moment focus lands on Projects.
- **D-07:** Do NOT add explicit Tab/Shift+Tab bindings to `BINDINGS`. Rely on Textual's default focus-chain Tab behavior. The focusable widget order in `compose()` (TL→TR→BL→BR) determines cycling. Shift+Tab works out of the box.

### Stub Panes
- **D-08:** Create minimal widget classes now: `TerminalPane` and `WorktreePane` in `src/joy/widgets/`. Each is a bordered container with a title and a centered muted "coming soon" message. Phase 9 will flesh out `WorktreePane`; Phase 12 will flesh out `TerminalPane`. Defining the classes now keeps diffs small and focused in those later phases.
- **D-09:** Stub content: a bordered pane with its title set via `border_title` (e.g., "Terminal", "Worktrees") and a centered `Static("coming soon")` body. Muted styling so the placeholder reads as intentional, not broken.
- **D-10:** The stub pane classes must be focusable — so Tab can land on them — but have no interactive keybindings. They participate in the focus cycle but consume no keys.

### Focus Indicator
- **D-11:** All four panes get a subtle border via CSS. The focused pane's border switches to an accent color (TCSS `:focus-within` on the pane container, falling back to `:focus` where needed). Clear at a glance, works across colorblind palettes, consistent with common Textual patterns.
- **D-12:** Border style is uniform across panes (no per-pane decorative differences) — only the color changes with focus.

### Footer / Sub-title
- **D-13:** Extend `on_descendant_focus` in `JoyApp` (`src/joy/app.py:69-80`) to set `sub_title` to the focused pane's name: "Projects" / "Detail" / "Terminal" / "Worktrees". Preserves the v1.0 pattern where the header shows what's focused.
- **D-14:** Do NOT add Tab/Shift+Tab to the Footer. Rely on Textual's default Tab behavior (also D-07). Keeps the minimalist footer uncluttered; Tab is a universal TUI convention.
- **D-15:** Per-pane keybindings in the Footer continue to use Textual's existing focus-chain resolution — widget `BINDINGS` appear when that widget (or a descendant) has focus. No new logic needed; existing ProjectList/ProjectDetail bindings already behave this way.

### Claude's Discretion
- Exact border colors / accent color choice (pick something visible in the default Textual palette; must remain readable on both dark and light terminals).
- Whether to extract the `Grid` CSS to a `.tcss` file or keep it in the `CSS = """..."""` class attribute on `JoyApp`. Use whichever is cleaner given the existing pattern — current code keeps CSS inline, so continue that unless it gets unwieldy.
- Exact wording and styling of "coming soon" text (muted dim styling, centered).
- Whether `TerminalPane` and `WorktreePane` subclass `Container`, `Static`, or `Widget` — choose whatever makes them focusable with minimum ceremony.
- Internal pane IDs for CSS targeting (suggest `#projects-pane`, `#detail-pane`, `#terminal-pane`, `#worktrees-pane`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` §"Phase 8: 4-Pane Layout" (lines 67-76) — Goal, requirements PANE-01/PANE-02, success criteria, UI hint
- `.planning/PROJECT.md` — Core value, v1.0 delivered features (two-pane layout, Footer with key hints, Escape navigation), non-goals

### Existing code to preserve
- `src/joy/app.py` — Current `JoyApp.compose()` with `Horizontal(ProjectList, ProjectDetail)`, CSS on lines 25-28, `on_descendant_focus` on lines 69-80, BINDINGS on lines 30-35
- `src/joy/widgets/project_list.py` — `ProjectList` and `JoyListView` widgets used in top-left pane
- `src/joy/widgets/project_detail.py` — `ProjectDetail` widget used in top-right pane

### Testing baseline (regression)
- `tests/test_app.py` (if exists) — Existing app-level tests that must keep passing
- `tests/test_models.py`, `tests/test_worktrees.py`, `tests/test_*.py` — Full suite must remain green (188+ tests at end of Phase 7)

### Future-phase anchors (do NOT implement in Phase 8)
- `.planning/ROADMAP.md` §"Phase 9: Worktree Pane" — `WorktreePane` stub defined here will be filled in next phase
- `.planning/ROADMAP.md` §"Phase 12: iTerm2 Integration & Terminal Pane" — `TerminalPane` stub will be filled in later

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Horizontal` container pattern in `app.py` — informs how to compose the new `Grid`
- `on_descendant_focus` pattern on `JoyApp` — direct template for extending sub_title logic to 4 panes
- `src/joy/widgets/` directory structure — already hosts `ProjectList`, `ProjectDetail`, `object_row`; new `TerminalPane`/`WorktreePane` fit the same layout
- Textual `border_title` attribute — clean way to label each pane
- Existing CSS on `JoyApp` class (`CSS = """..."""`) — will be extended with grid rules rather than introducing a separate `.tcss` file

### Established Patterns
- Inline CSS on the App class, not an external `.tcss` file (current convention)
- Widgets live in `src/joy/widgets/` with one class per file
- `BINDINGS` at widget and app level, with Textual's focus-chain resolution for Footer key hints
- `on_descendant_focus` walks up the DOM to identify which pane owns the focused widget — already in use in `app.py:69-80`

### Integration Points
- `JoyApp.compose()` at `app.py:39-45` — the grid replacement point
- `JoyApp.on_descendant_focus()` at `app.py:69-80` — sub_title extension point; add branches for `#terminal-pane` and `#worktrees-pane`
- `JoyApp.CSS` at `app.py:25-28` — grid layout rules go here (or into a file if it grows large)
- `src/joy/widgets/__init__.py` — export `TerminalPane` and `WorktreePane` for tidy imports

</code_context>

<specifics>
## Specific Ideas

- Focus indicator should feel like common TUI patterns (e.g., lazygit / k9s panes) — bordered panes, accent-colored border on focus.
- "coming soon" should read as intentional placeholder, not a bug — muted styling, centered.
- Snappiness matters: focus switching with Tab must feel instantaneous. Don't add work on focus change beyond updating sub_title.

</specifics>

<deferred>
## Deferred Ideas

- User-resizable splits / draggable pane borders — keyboard-driven tool; not needed.
- Terminal pane content (iTerm2 sessions, Claude detection) — Phase 12.
- Worktree pane content (grouped list, status indicators) — Phase 9.
- Background refresh on pane data — Phase 10.
- Persisting "which pane was last focused" across app restarts — future consideration, not required by PANE-01/PANE-02.
- Per-pane keybindings cheatsheet overlay — Textual's default Footer + widget BINDINGS resolution is sufficient for v1.1.

</deferred>

---

*Phase: 08-4-pane-layout*
*Context gathered: 2026-04-13*
