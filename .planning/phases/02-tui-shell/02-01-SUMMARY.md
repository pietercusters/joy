---
phase: "02-tui-shell"
plan: "01"
subsystem: "tui-shell"
tags: ["textual", "tui", "layout", "navigation", "widgets"]

dependency_graph:
  requires: ["01-foundation"]
  provides: ["tui-entry-point", "two-pane-layout", "project-list-widget", "project-detail-stub"]
  affects: ["02-02-object-rows", "02-03-footer"]

tech_stack:
  added: ["textual==8.2.3", "rich==14.3.3", "markdown-it-py==4.0.0"]
  patterns: ["Textual App with @work(thread=True) async data loading", "Message-based widget communication", "Lazy store import inside worker"]

key_files:
  created:
    - "pyproject.toml (textual>=8.2 added)"
    - "src/joy/widgets/__init__.py"
    - "src/joy/widgets/project_list.py"
    - "src/joy/widgets/project_detail.py"
  modified:
    - "src/joy/app.py (replaced stub with JoyApp class)"
    - "uv.lock (10 new packages including textual 8.2.3)"

decisions:
  - "1fr:2fr CSS ratio for project-list:project-detail pane split (D-09)"
  - "Lazy store import inside @work(thread=True) worker to avoid blocking startup (CP-1, CP-2)"
  - "ProjectList.can_focus=False, inner ListView handles focus natively"
  - "ProjectDetail.can_focus=True with Escape binding to return focus (D-06, CORE-04)"
  - "Message-based communication between widgets: ProjectHighlighted and ProjectSelected"

metrics:
  duration: "92 seconds"
  completed_date: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 2
---

# Phase 02 Plan 01: TUI Shell App Foundation Summary

**One-liner:** Textual 8.2 two-pane app with async project loading, ListView navigation, and Enter/Escape focus management between panes.

## What Was Built

Replaced the `joy` CLI stub (`print("Not yet implemented")`) with a full Textual TUI app. The app launches via `uv run joy` and shows a two-pane layout (33% project list, 67% detail stub) that navigates with keyboard only.

### Files Created

- **`src/joy/widgets/__init__.py`** — widgets subpackage marker
- **`src/joy/widgets/project_list.py`** — `ProjectList` widget wrapping Textual `ListView`, posts `ProjectHighlighted` and `ProjectSelected` messages
- **`src/joy/widgets/project_detail.py`** — `ProjectDetail` stub widget (can_focus=True) with Escape binding to return focus, displays project name + object count
- **`src/joy/app.py`** (rewritten) — `JoyApp(App)` with 1fr:2fr CSS layout, `@work(thread=True)` async data loading, lazy store import, message handlers for both pane transitions

### Files Modified

- **`pyproject.toml`** — added `textual>=8.2` to dependencies
- **`uv.lock`** — resolved textual 8.2.3 + 9 transitive dependencies

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create JoyApp class with two-pane layout and async data loading | dcb555d | pyproject.toml, app.py, widgets/__init__.py, widgets/project_detail.py |
| 2 | Create ProjectList widget with keyboard navigation and focus management | 0ca1905 | widgets/project_list.py |
| - | Update uv.lock | a69541f | uv.lock |

## Navigation Model Implemented

- Arrow keys / j/k in project list (ListView built-in)
- Enter on project: updates detail pane + shifts focus to right (D-04)
- Escape in detail pane: returns focus to project list ListView (D-06, CORE-04)
- First project auto-selected on startup (PROJ-02)
- `q` binds to quit globally

## Deviations from Plan

None — plan executed exactly as written. ProjectList widget was created during Task 1 implementation (before Task 1 commit) since app.py imports it, but committed as Task 2.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `ProjectDetail.set_project()` shows only name + object count | `src/joy/widgets/project_detail.py` | 30-34 | Intentional stub. Plan 02-02 will replace with full object row rendering grouped by PresetKind. |
| `Static("Select a project")` placeholder | `src/joy/widgets/project_detail.py` | 22 | Intentional stub. Cleared on first project highlight/select. |

These stubs do NOT prevent the plan's goal (two-pane navigation shell). They are the defined scope boundary for Plan 02-02.

## Threat Flags

No new threat surface beyond what's in the plan's threat model. Textual's Rich rendering sanitizes project name display (T-2-01-02 accept disposition confirmed — no raw terminal writes).

## Self-Check: PASSED

Files exist:
- src/joy/widgets/__init__.py: FOUND
- src/joy/widgets/project_list.py: FOUND
- src/joy/widgets/project_detail.py: FOUND
- src/joy/app.py: FOUND (rewritten)

Commits exist:
- dcb555d: FOUND (feat(02-01): create JoyApp class...)
- 0ca1905: FOUND (feat(02-01): create ProjectList widget...)
- a69541f: FOUND (chore(02-01): update uv.lock...)
