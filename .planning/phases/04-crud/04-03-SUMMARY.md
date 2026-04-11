---
phase: 04-crud
plan: "03"
subsystem: app-bindings
tags: [crud, tdd, textual, bindings, modal, edit-object, delete-object, delete-project]
dependency_graph:
  requires:
    - src/joy/screens/value_input.py (ValueInputModal with existing_value — Plan 01 output)
    - src/joy/screens/confirmation.py (ConfirmationModal — Plan 01 output)
    - src/joy/widgets/project_detail.py (_save_toggle, _render_project, highlighted_object — Plan 02 output)
    - src/joy/widgets/project_list.py (select_index, JoyListView — Plan 02 output)
    - src/joy/app.py (_save_projects_bg — Plan 02 output)
  provides:
    - src/joy/widgets/project_detail.py (action_edit_object, action_delete_object, _set_project_with_cursor)
    - src/joy/widgets/project_list.py (action_delete_project on JoyListView)
    - tests/test_tui.py (7 new integration tests for MGMT-02, MGMT-03, PROJ-05)
  affects:
    - Phase 05 settings/distribution (full CRUD now complete, no further mutations needed)
tech-stack:
  added: []
  patterns:
    - Lazy imports (noqa PLC0415) inside action methods to avoid circular import between project_detail and joy.screens
    - _set_project_with_cursor() helper pattern for cursor-preserving re-render after mutation
    - initial_cursor keyword arg on _render_project() for post-delete cursor positioning
    - action_delete_project() on JoyListView accessing parent ProjectList via app.query_one("#project-list")

key-files:
  created: []
  modified:
    - src/joy/widgets/project_detail.py
    - src/joy/widgets/project_list.py
    - tests/test_tui.py

key-decisions:
  - "Lazy imports inside action methods (not top-level) to break circular import: project_detail.py -> joy.screens -> preset_picker.py -> project_detail.py"
  - "_render_project extended with initial_cursor keyword arg to support cursor restoration after delete without a second re-render pass"
  - "action_delete_project implemented on JoyListView (not ProjectList) to get direct access to listview.index for current selection"

patterns-established:
  - "Circular import pattern: use noqa PLC0415 lazy imports inside methods when two widgets need each other's types"
  - "Cursor restoration pattern: capture _cursor before mutation, pass as initial_cursor to _set_project_with_cursor"
  - "Post-delete selection: min(index, len(projects) - 1) gives adjacent-or-previous behavior without an if/else"

requirements-completed: [MGMT-02, MGMT-03, PROJ-05]

duration: 8min
completed: "2026-04-11"
---

# Phase 4 Plan 03: Edit Object, Delete Object, and Delete Project Flows Summary

**e/d bindings wire edit and delete for objects; D/delete binding wires project deletion — completing all 5 CRUD flows with confirmation modals, cursor management, and background persistence.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-11T09:24:49Z
- **Completed:** 2026-04-11T09:32:16Z
- **Tasks:** 2 of 3 (Task 3 is human-verify checkpoint)
- **Files modified:** 3

## Accomplishments
- Edit object (e) opens ValueInputModal pre-populated with current value; confirmed edit persists via background thread
- Delete object (d) opens ConfirmationModal, then removes object by identity index with cursor restored to prev-1
- Delete project (D/delete) opens ConfirmationModal, removes project, selects adjacent (or clears detail if last project)
- 7 integration tests added (total suite: 114 tests passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire e and d bindings into ProjectDetail** - `24d4ed5` (feat)
2. **Task 2: Wire D/delete project deletion and integration tests** - `e3601d3` (feat)
3. **Task 3: Visual verification checkpoint** - awaiting human verification

## Files Created/Modified
- `src/joy/widgets/project_detail.py` - Added e/d bindings, action_edit_object(), action_delete_object(), _set_project_with_cursor(), extended _render_project() with initial_cursor
- `src/joy/widgets/project_list.py` - Added D/delete bindings and action_delete_project() on JoyListView
- `tests/test_tui.py` - Added 7 integration tests: test_e_edits_object, test_e_no_object_shows_error, test_d_deletes_object, test_d_escape_noop, test_D_deletes_project, test_D_escape_noop, test_D_selects_adjacent

## Decisions Made

1. **Lazy imports to break circular dependency** — `project_detail.py` cannot import `joy.screens` at module level because `joy.screens.__init__` imports `preset_picker.py` which imports `GROUP_ORDER` from `project_detail.py`. Fixed with lazy imports inside the action methods using `# noqa: PLC0415`.

2. **`_render_project` extended with `initial_cursor` keyword arg** — Rather than a second render pass or separate cursor-set method, the initial_cursor is passed through the call_after_refresh lambda. This keeps cursor positioning as part of the single render cycle.

3. **`action_delete_project` on JoyListView (not ProjectList)** — JoyListView has direct access to `self.index` (current highlighted item). ProjectList doesn't expose this. Placing the method on JoyListView is consistent with where the binding fires.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed circular import between project_detail.py and joy.screens**
- **Found during:** Task 1 (initial import verification)
- **Issue:** Plan specified top-level `from joy.screens import ConfirmationModal, ValueInputModal` in project_detail.py. This creates a circular import: project_detail -> joy.screens -> preset_picker -> project_detail (for GROUP_ORDER)
- **Fix:** Moved imports inside the action methods as lazy imports with `# noqa: PLC0415`
- **Files modified:** src/joy/widgets/project_detail.py
- **Verification:** `uv run python -c "from joy.widgets.project_detail import ProjectDetail"` succeeds; 114 tests pass
- **Committed in:** 24d4ed5 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix was necessary for the code to compile. Pattern is consistent with existing lazy imports in the codebase (e.g., operations.py lazy import in _do_open).

## Issues Encountered

None beyond the circular import deviation documented above.

## Known Stubs

None — all three CRUD flows (edit object, delete object, delete project) are fully wired end-to-end with real modal screens, live mutation, and TOML persistence.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. All changes are within the existing single-user local TOML store boundary:
- T-4-11 (Tampering / edit value): ValueInputModal strips input; all notify() calls use markup=False
- T-4-13 (DoS / last project): `if projects` guard before `min()` prevents IndexError when deleting last project; detail pane explicitly cleared

## Next Phase Readiness
- Full Phase 4 CRUD capability complete (create project, add object, edit object, delete object, delete project)
- Task 3 is a human-verify checkpoint — user should run `uv run joy` and verify all 5 CRUD flows
- Phase 5 (settings/distribution) can proceed after visual verification

---
*Phase: 04-crud*
*Completed: 2026-04-11*
