---
phase: 04-crud
plan: "02"
subsystem: app-bindings
tags: [crud, tdd, textual, bindings, modal, project-create, add-object]
dependency_graph:
  requires:
    - src/joy/screens/name_input.py (NameInputModal — Plan 01 output)
    - src/joy/screens/preset_picker.py (PresetPickerModal — Plan 01 output)
    - src/joy/screens/value_input.py (ValueInputModal — Plan 01 output)
    - src/joy/models.py (Project, ObjectItem, PresetKind)
    - src/joy/store.py (save_projects)
    - src/joy/widgets/project_list.py (ProjectList, JoyListView)
    - src/joy/widgets/project_detail.py (ProjectDetail)
  provides:
    - src/joy/app.py (action_new_project, _start_add_object_loop, _save_projects_bg)
    - src/joy/widgets/project_detail.py (action_add_object)
    - src/joy/widgets/project_list.py (select_index)
    - tests/test_tui.py (6 new integration tests for PROJ-04 and MGMT-01)
  affects:
    - Plan 03 (delete/rename flows will reuse _save_projects_bg and modal patterns)
tech_stack:
  added: []
  patterns:
    - priority=True bindings on JoyApp for global key capture from both panes
    - push_screen(Modal(), callback) chaining for multi-step flows
    - Recursive _start_add_object_loop via callback re-entry (no explicit loop)
    - @work(thread=True, exit_on_error=False) for background TOML persistence
    - markup=False on all notify() calls (T-4-08 mitigation)
key_files:
  created: []
  modified:
    - src/joy/app.py
    - src/joy/widgets/project_detail.py
    - src/joy/widgets/project_list.py
    - tests/test_tui.py
decisions:
  - "_start_add_object_loop uses recursive callback re-entry rather than an explicit loop — Textual's async screen stack makes recursion the natural pattern; each call pushes a fresh PresetPickerModal and chains its own on_preset callback"
  - "_save_projects_bg is a shared background saver used by both action_new_project and _start_add_object_loop to avoid code duplication per D-16"
  - "select_index() added to ProjectList to encapsulate listview.index mutation — cleaner than direct widget access from app.py"
metrics:
  duration: "5m 49s"
  completed: "2026-04-11T09:24:49Z"
  tasks_completed: 2
  files_created: 0
  files_modified: 4
---

# Phase 4 Plan 02: Create Project and Add Object Flows Summary

n binding triggers two-step project creation (name modal + add-object loop); a binding in detail pane adds objects to the current project — both persist via background thread.

## What Was Built

### src/joy/app.py — New methods

**`action_new_project()`** (triggered by `Binding("n", "new_project", "New", priority=True)`)
- Pushes NameInputModal; on_name callback handles the result
- Duplicate name check: rejects with `notify(..., severity="error", markup=False)` (T-4-06 mitigation)
- Creates `Project(name=name)`, appends to `_projects`, calls `_save_projects_bg()`
- Calls `project_list.set_projects()` and `select_index()` to refresh UI and select new project
- Calls `_start_add_object_loop(project)` immediately after creation (D-02, D-03)

**`_start_add_object_loop(project: Project)`**
- Pushes PresetPickerModal; on_preset callback chains to ValueInputModal push
- on_value callback: if value not None, creates ObjectItem, appends to project.objects, saves, refreshes detail
- Recursively calls `_start_add_object_loop(project)` after each value result to implement the loop (D-03)
- Escape on PresetPickerModal returns None → on_preset returns immediately, ending the loop

**`_save_projects_bg()`**
- `@work(thread=True, exit_on_error=False)` background worker
- Calls `save_projects(self._projects)` with lazy import per project pattern

### src/joy/widgets/project_detail.py — New binding and method

**`Binding("a", "add_object", "Add")`** added to BINDINGS.

**`action_add_object()`**
- Guards `if self._project is None: return`
- Delegates to `self.app._start_add_object_loop(self._project)` (D-05, D-07)

### src/joy/widgets/project_list.py — New helper method

**`select_index(index: int)`**
- Encapsulates `listview.index = index` for cleaner app.py code
- Guards bounds: `if 0 <= index < len(self._projects)`

### tests/test_tui.py — 6 new integration tests

| Test | Covers |
|------|--------|
| test_n_creates_project | PROJ-04: n -> name -> Enter -> project in list |
| test_n_escape_noop | PROJ-04: n -> Escape -> no change |
| test_n_duplicate_name_error | PROJ-04: duplicate name rejected |
| test_n_persists | PROJ-04: save_projects called after creation |
| test_a_adds_object | MGMT-01: a -> filter "wo" -> Enter -> value -> Enter adds worktree |
| test_a_escape_noop | MGMT-01: a -> Escape -> no object added |

## Decisions Made

1. **Recursive callback re-entry for add-object loop** — `_start_add_object_loop` re-calls itself at the end of the on_value callback. This is the natural Textual pattern: `push_screen` schedules async screen transitions and callbacks fire after each dismiss. An explicit `while` loop would block the event loop.

2. **`_save_projects_bg` as shared utility** — Both `action_new_project` and `_start_add_object_loop` call this method. Avoids copy-pasting the `@work` decorator and lazy import pattern. Any future mutation action can also use it.

3. **`select_index()` helper on ProjectList** — The plan mentioned accessing the listview directly from app.py, but encapsulating in ProjectList keeps widget internals private and follows the existing `select_first()` pattern.

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria met on first pass.

## Known Stubs

None — both `n` and `a` flows are fully wired end-to-end with real modal screens, live project mutation, and TOML persistence.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. All changes are within the existing single-user local TOML store boundary. All notify() calls use `markup=False` per T-4-08. Duplicate name check is present per T-4-06. The recursive push_screen loop is bounded by user Escape per T-4-07 analysis.

## Self-Check: PASSED

All 4 modified files present on disk. Both task commits exist (79f6b90, 9b993d9). 107 tests pass (101 pre-existing + 6 new).
