---
phase: 02-tui-shell
plan: 03
subsystem: ui
tags: [textual, tui, testing, pytest-asyncio, footer, header, keybindings]

requires:
  - phase: 02-01
    provides: JoyApp shell with ProjectList and ProjectDetail widgets
  - phase: 02-02
    provides: Full ProjectDetail with ObjectRow, grouped display, cursor nav

provides:
  - Context-sensitive Header showing pane label (Projects/Detail)
  - Footer with binding display that changes on focus shift
  - 5 Textual pilot tests covering startup, auto-select, Enter, Escape, quit
  - JoyListView subclass with j/k vim navigation

affects: [03-activation, testing]

tech-stack:
  added: [pytest-asyncio>=0.25]
  patterns:
    - on_descendant_focus for App-level focus awareness (not watch_focused)
    - JoyListView subclass pattern for adding vim bindings to Textual widgets

key-files:
  created:
    - tests/test_tui.py
  modified:
    - src/joy/app.py
    - src/joy/widgets/project_list.py
    - pyproject.toml

key-decisions:
  - "Use on_descendant_focus not watch_focused — App.focused is a property, not a reactive"
  - "JoyListView(ListView) subclass to add j/k without modifying Textual internals"
  - "Header SUB_TITLE for pane label (Option A) over Footer subclassing (Option B)"

patterns-established:
  - "Focus detection: use on_descendant_focus on App, walk node.parent chain to find pane ID"
  - "Vim navigation: subclass Textual widget, add BINDINGS with show=False to avoid footer clutter"

requirements-completed: [CORE-03, CORE-04, CORE-06, CORE-07]

duration: ~45min
completed: 2026-04-10
---

# Plan 02-03: Context-Sensitive Footer + Pilot Tests Summary

**Context-aware Header/Footer with pane labels and binding display, 5 Textual pilot tests, and vim j/k on project list**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-04-10
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 4

## Accomplishments
- Header subtitle updates to "Projects" or "Detail" as focus shifts between panes
- Footer shows context-sensitive bindings: list pane shows up/down/enter/q, detail pane shows j/k/escape/q
- 5 pilot tests via `pytest-asyncio` + Textual `run_test()`: launch, auto-select, Enter focus, Escape return, quit
- j/k vim navigation on project list via `JoyListView` subclass
- Fixed `ListView.Highlighted` API: `event.index` → `event.list_view.index` (Textual 8.x)

## Task Commits

1. **Task 1: Context-sensitive header and footer** — `69a3e53` (feat)
2. **Task 2: Textual pilot tests + ListView bug fix** — `a6bdf7e` (feat)
3. **Task 3: Visual verification** — human checkpoint, approved by user
4. **Bug fix: on_descendant_focus + JoyListView** — `2a41518` (fix)

## Files Created/Modified
- `src/joy/app.py` — Header/Footer in compose, on_descendant_focus for sub_title updates
- `tests/test_tui.py` — 5 async pilot tests with mock_store fixture
- `pyproject.toml` — pytest-asyncio dev dependency
- `src/joy/widgets/project_list.py` — JoyListView subclass, event.list_view.index fix

## Decisions Made
- **Header for pane label, not Footer subclass:** Simpler and cleaner; Header's SUB_TITLE is purpose-built for context labels
- **on_descendant_focus over watch_focused:** `App.focused` is a `@property` delegating to `Screen.focused`, not an App reactive — `watch_focused` is dead code on App subclasses
- **JoyListView(ListView) subclass:** Cleanest way to add j/k without forking Textual; `show=False` keeps j/k out of the footer binding display

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] watch_focused is dead code on App**
- **Found during:** Task 3 visual verification (human)
- **Issue:** Plan used `watch_focused` to update sub_title, but `App.focused` is a property not a reactive — the method never fires
- **Fix:** Replaced with `on_descendant_focus(self, event)` which fires via Textual's descendant focus notification system; walk `event.widget` up the DOM
- **Files modified:** src/joy/app.py
- **Committed in:** 2a41518

**2. [Rule 1 - Bug] ListView.Highlighted has no .index attribute in Textual 8.x**
- **Found during:** Task 2 (pilot test failures)
- **Issue:** `event.index` on `ListView.Highlighted` crashes; correct API is `event.list_view.index`
- **Fix:** Changed to `index = event.list_view.index`
- **Files modified:** src/joy/widgets/project_list.py
- **Committed in:** a6bdf7e

**3. [Rule 1 - Bug] j/k not working on project list**
- **Found during:** Task 3 visual verification (human)
- **Issue:** Textual's ListView has up/down built-in but NOT j/k; plan assumed j/k were built-in
- **Fix:** Created `JoyListView(ListView)` subclass with j/k BINDINGS mapped to cursor_up/cursor_down
- **Files modified:** src/joy/widgets/project_list.py
- **Committed in:** 2a41518

---

**Total deviations:** 3 auto-fixed (all bugs: 2 Textual 8.x API surprises, 1 missing built-in)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered
- Parallel worktree execution (02-02 and 02-03 on separate branches from Wave 1 HEAD) meant the 02-03 checkpoint worktree lacked 02-02's ProjectDetail implementation. Human verification was initially run against the wrong base; re-run on main after merging both branches passed.

## Next Phase Readiness
- Complete read-only TUI shell: two-pane layout, project list, grouped object display with icons, cursor navigation, focus management, context-aware footer
- `highlighted_object` property on ProjectDetail ready for Phase 3's `o` activation key
- All pilot tests pass: `uv run pytest tests/test_tui.py -x -v`

---
*Phase: 02-tui-shell*
*Completed: 2026-04-10*
