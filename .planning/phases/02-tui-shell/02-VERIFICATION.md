---
phase: 02-tui-shell
verified: 2026-04-10T22:00:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run `uv run joy` in a Nerd Font terminal and verify two-pane layout with icons"
    expected: "Two panes visible (~33%/67% split), project list on left, object detail on right, Nerd Font icons on each object row"
    why_human: "Terminal rendering, font support, and visual proportions cannot be verified programmatically"
  - test: "Navigate project list with j/k and arrow keys, confirm detail pane updates immediately"
    expected: "Highlight moves on keypress; right pane content changes to reflect newly highlighted project"
    why_human: "Real-time pane update on cursor move requires visual confirmation in a live terminal"
  - test: "Press Enter to move to detail pane, use j/k to move cursor through object rows, confirm full-row highlight"
    expected: "Cursor visible as full-width background highlight on the current row; j/k advances/retreats the highlight"
    why_human: "CSS --highlight class rendering requires visual inspection in a running terminal"
  - test: "Press Escape from detail pane; confirm focus returns to project list (no focus trap)"
    expected: "Project list is active and j/k navigate it again; no key press is lost or ignored"
    why_human: "Focus trap detection requires interactive testing"
  - test: "Check footer/header area: header shows 'Projects' when list is focused, 'Detail' when detail is focused; footer shows context-appropriate binding hints"
    expected: "Header subtitle switches between 'Projects' and 'Detail'; footer changes bindings shown"
    why_human: "Header subtitle rendering and footer binding display require visual inspection in a running terminal"
  - test: "Check long object values are truncated with no line wrapping"
    expected: "Each object row occupies exactly one line; long URLs/paths are cut off at the pane boundary"
    why_human: "Text overflow/ellipsis behavior depends on actual terminal width and font metrics"
---

# Phase 2: TUI Shell Verification Report

**Phase Goal:** Build the complete read-only TUI shell — two-pane layout (project list left, detail right), project objects rendered with Nerd Font icons grouped by type, keyboard navigation, and context-sensitive footer/header showing available bindings and pane label.
**Verified:** 2026-04-10T22:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | App launches and shows a two-pane layout: project list (left) with selection highlighting, project detail (right) showing objects with Nerd Font icons | VERIFIED (code) / ? human (visual) | `app.py` composes `Horizontal(ProjectList, ProjectDetail)` 1fr:2fr; `object_row.py` has `PRESET_ICONS` dict with all 9 PresetKind values; pilot test `test_app_launches_with_two_panes` passes |
| 2 | User can navigate the project list with j/k or arrow keys; selecting a project immediately updates the detail pane | VERIFIED (code) / ? human (visual) | `JoyListView(ListView)` subclass adds j/k BINDINGS; `on_project_list_project_highlighted` calls `detail.set_project()` on every highlight change; pilot test `test_first_project_auto_selected` confirms detail populated |
| 3 | First project is auto-selected on startup so the detail pane is never empty | VERIFIED | `_set_projects` calls `select_first()` when projects list non-empty; `test_first_project_auto_selected` passes (detail._project.name == "project-alpha") |
| 4 | Footer displays context-sensitive keyboard hints that update when focus changes between panes | VERIFIED (code) / ? human (visual) | `on_descendant_focus` walks DOM to set `sub_title` to "Projects" or "Detail"; Textual `Footer()` in compose reads bindings from focus chain; needs visual confirmation |
| 5 | Pressing Escape always navigates back with no focus traps; app starts in under 350ms to first paint | VERIFIED (code) / ? human (timing) | `action_focus_list` returns focus to `#project-listview`; pilot test `test_escape_returns_focus_to_list` passes; startup timing needs human measurement |

**Score:** 5/5 truths verified (programmatic checks pass; 6 visual/interactive behaviors need human confirmation)

### Must-Have Truths from Plan Frontmatter

All plan-level truths are covered by the roadmap truths above. Cross-check:

**Plan 01 truths (all VERIFIED):**
- "App launches with `uv run joy` and shows a two-pane layout" — pilot test passes
- "Left pane shows project names loaded from ~/.joy/projects.toml" — `set_projects` populates `JoyListView` from loaded data; mock confirms wiring
- "First project is auto-selected on startup (highlighted)" — `test_first_project_auto_selected` passes
- "Pressing Enter on a project shifts focus to the right pane" — `test_enter_shifts_focus_to_detail` passes
- "Pressing Escape in the right pane returns focus to the left pane" — `test_escape_returns_focus_to_list` passes
- "App starts in under 350ms to first paint" — NEEDS HUMAN (cannot measure from test runner)

**Plan 02 truths (all VERIFIED):**
- "Detail pane shows objects grouped by preset type with header rows" — `_render_project` iterates `GROUP_ORDER`, mounts `GroupHeader` per non-empty kind
- "Each object row shows Nerd Font icon + label + value" — `ObjectRow._render_text` returns `f"{icon}  {label}  {value}"`; all 9 icons in `PRESET_ICONS`
- "Long values are right-truncated with ellipsis" — `ObjectRow.DEFAULT_CSS` has `height: 1; overflow: hidden` — NEEDS HUMAN (visual)
- "j/k and up/down navigate a cursor through object rows" — `action_cursor_up/down` on `ProjectDetail`; `BINDINGS` contains all four keys
- "Selected object row has a full-row background highlight" — `ObjectRow.--highlight { background: $accent }` in `ProjectDetail.DEFAULT_CSS` — NEEDS HUMAN (visual)
- "Navigating the project list immediately updates the detail pane" — `on_project_list_project_highlighted` confirmed wired

**Plan 03 truths (all VERIFIED):**
- "Footer shows context-sensitive bindings that change when focus shifts" — `on_descendant_focus` sets `sub_title`; Textual `Footer()` present
- "Header subtitle shows pane context label (Projects or Detail)" — `sub_title` assignments to "Projects"/"Detail" confirmed in `app.py`
- "All available bindings for the current pane context are shown" — Textual `Footer` auto-reads from focus chain; NEEDS HUMAN (visual)
- "Escape from detail pane returns to project list with no focus traps" — `test_escape_returns_focus_to_list` passes
- "App startup time is under 350ms to first paint" — NEEDS HUMAN

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | textual dependency declaration | VERIFIED | Contains `textual>=8.2` |
| `src/joy/app.py` | JoyApp Textual App class and main() entry point | VERIFIED | `class JoyApp(App)`, `def main()`, Header/Footer, on_descendant_focus |
| `src/joy/widgets/__init__.py` | widgets subpackage | VERIFIED | File exists |
| `src/joy/widgets/project_list.py` | ProjectList widget with ListView | VERIFIED | `class ProjectList(Widget, can_focus=False)`, `JoyListView` subclass with j/k |
| `src/joy/widgets/project_detail.py` | Full ProjectDetail with grouped objects and cursor navigation | VERIFIED | `class ProjectDetail(Widget, can_focus=True)`, all BINDINGS, `_update_highlight`, `highlighted_object` |
| `src/joy/widgets/object_row.py` | ObjectRow widget with icon, label, value display | VERIFIED | `class ObjectRow(Static)`, `PRESET_ICONS` all 9 kinds |
| `tests/test_tui.py` | Textual pilot tests for TUI behavior | VERIFIED | 5 test functions, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py` | `store.py` | `load_projects` call in worker | WIRED | Tool confirmed; lazy import inside `@work(thread=True)` |
| `app.py` | `project_list.py` | compose yields ProjectList | WIRED | Tool confirmed |
| `project_list.py` | `models.py` | `from joy.models import Project` | WIRED | Tool confirmed |
| `project_detail.py` | `models.py` | `from joy.models import` | WIRED | Tool confirmed |
| `object_row.py` | `models.py` | `from joy.models import` | WIRED | Tool confirmed |
| `project_detail.py` | `object_row.py` | composes ObjectRow widgets | WIRED | Tool confirmed |
| `app.py` | `project_list.py` | focus change triggers footer update | WIRED | Tool confirmed |
| `app.py` | `project_detail.py` | focus change triggers footer update | WIRED | Tool confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `ProjectList` | `_projects` | `store.load_projects()` via `@work(thread=True)` in `app.py` | Yes — reads `~/.joy/projects.toml` via `tomllib` | FLOWING |
| `ProjectDetail` | `_project` / `_rows` | `set_project()` called from `on_project_list_project_highlighted` | Yes — receives `Project` object from store data | FLOWING |
| `ObjectRow` | displayed text | `ObjectItem.kind`, `.label`, `.value` from real project data | Yes — passed directly from TOML-loaded `ObjectItem` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Two-pane layout DOM presence | `pytest tests/test_tui.py::test_app_launches_with_two_panes` | PASSED | PASS |
| First project auto-selected | `pytest tests/test_tui.py::test_first_project_auto_selected` | PASSED | PASS |
| Enter shifts focus to detail | `pytest tests/test_tui.py::test_enter_shifts_focus_to_detail` | PASSED | PASS |
| Escape returns focus to list | `pytest tests/test_tui.py::test_escape_returns_focus_to_list` | PASSED | PASS |
| q quits app | `pytest tests/test_tui.py::test_quit_with_q` | PASSED | PASS |
| Visual layout, icons, truncation, highlights, footer | `uv run joy` in terminal | — | SKIP (needs human) |

All 5 automated pilot tests pass (`5 passed in 1.63s`).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| CORE-01 | 02-01 | Two-pane layout | SATISFIED | `Horizontal(ProjectList, ProjectDetail)` in compose; pilot test passes |
| CORE-02 | 02-01, 02-02, 02-03 | j/k or arrow key navigation | SATISFIED | `JoyListView` subclass adds j/k; `ProjectDetail.BINDINGS` has j/k/up/down |
| CORE-03 | 02-03 | Footer shows context-sensitive hints | SATISFIED | `Footer()` + `on_descendant_focus` + `sub_title`; needs visual confirm |
| CORE-04 | 02-01, 02-03 | Escape always navigates back; no focus traps | SATISFIED | `action_focus_list` wired; pilot test passes |
| CORE-06 | 02-01, 02-03 | App starts in under 350ms | NEEDS HUMAN | Lazy import + `@work(thread=True)` architecture in place; actual timing needs human measurement |
| CORE-07 | 02-02 | Each object type displays a Nerd Font icon | SATISFIED | `PRESET_ICONS` dict covers all 9 `PresetKind` values; needs visual confirm |
| PROJ-01 | 02-01 | Project list visible on left pane with selection highlighting | SATISFIED | `ProjectList` with `JoyListView` renders names; `ListView` built-in highlight |
| PROJ-02 | 02-01 | First project auto-selected on startup | SATISFIED | `select_first()` called in `_set_projects`; pilot test confirms |
| PROJ-03 | 02-02 | Navigating project list updates detail pane immediately | SATISFIED | `on_project_list_project_highlighted` calls `set_project()` immediately |

All 9 Phase 2 requirements have implementation evidence. CORE-06 timing and CORE-07/CORE-03 visual rendering still require human observation.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | No TODOs, stubs, or empty implementations found in any phase 2 file | — | — |

Checked files: `app.py`, `project_list.py`, `project_detail.py`, `object_row.py`, `test_tui.py`. No placeholder comments, empty returns, or hardcoded empty data arrays found that flow to rendering. `return null` in `highlighted_object` is correct sentinel behavior (no selection), not a stub.

### Human Verification Required

#### 1. Two-Pane Visual Layout

**Test:** Run `uv run joy` in a terminal with a Nerd Font (e.g., FiraCode Nerd Font). Observe the initial screen.
**Expected:** Two panes visible — left ~33% wide with project names listed and first project highlighted; right ~67% wide with the first project's objects displayed grouped by type (Worktrees, Branches, Merge Requests, etc.) each with a distinct Nerd Font icon on the left of each row.
**Why human:** Terminal font rendering, widget proportions, and icon character display cannot be asserted programmatically.

#### 2. Navigation Updates Detail Pane

**Test:** Use j/k or arrow keys to move through the project list.
**Expected:** Detail pane content changes immediately to reflect the newly highlighted project. No lag or flicker.
**Why human:** Real-time reactive rendering requires live terminal observation.

#### 3. Cursor Highlight in Detail Pane

**Test:** Press Enter to move focus to detail pane; press j/k to move through object rows.
**Expected:** A full-width background highlight (accent color) moves between object rows. Group headers are skipped by the cursor.
**Why human:** CSS `--highlight` class with `background: $accent` rendering requires visual inspection.

#### 4. Footer/Header Context Labels

**Test:** Tab between panes or use Enter/Escape; observe header and footer.
**Expected:** Header shows "joy / Projects" when project list is focused; "joy / Detail" when detail pane is focused. Footer shows different binding hints for each pane.
**Why human:** Header subtitle and Footer binding list content require visual confirmation in a running terminal.

#### 5. Text Truncation

**Test:** Add an object with a very long value (e.g., a long URL) to `~/.joy/projects.toml` and launch joy.
**Expected:** The object row occupies exactly one line; the long value is cut off at the pane boundary with no line wrapping.
**Why human:** Text overflow rendering depends on actual terminal width and font metrics.

#### 6. Startup Time Under 350ms

**Test:** Run `time uv run joy` in a non-TTY context, or use a stopwatch to measure time from command invocation to first render in the terminal.
**Expected:** First paint appears within 350ms.
**Why human:** Startup timing must be measured in the actual execution environment.

### Gaps Summary

No blocking gaps found. All artifacts exist and are substantive, all key links are wired, all data flows are connected, and all 5 automated pilot tests pass.

The 6 human verification items above are standard visual/interactive checks that automated tools cannot assess. They are required before the phase can be marked `passed`.

---

_Verified: 2026-04-10T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
