---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/widgets/project_list.py
  - src/joy/app.py
  - src/joy/widgets/hint_bar.py
  - tests/test_filter.py
autonomous: true
must_haves:
  truths:
    - "Pressing / in the project list does nothing (no filter input appears)"
    - "No Input widget with id 'filter-input' exists anywhere in the project list DOM"
    - "All existing project list functionality (cursor nav, new, rename, delete, archive, repo assign, status toggle) still works"
    - "The test suite passes with zero filter-related tests"
  artifacts:
    - path: "src/joy/widgets/project_list.py"
      provides: "ProjectList without filter functionality"
    - path: "src/joy/app.py"
      provides: "Hint bar text without /: Filter"
  key_links:
    - from: "src/joy/widgets/project_list.py"
      to: "BINDINGS"
      via: "No slash binding present"
---

<objective>
Remove the project list filter feature entirely: the "/" slash command binding, the filter Input widget, all filter event handlers, and the entire test_filter.py test file.

Purpose: Clean up unwanted UI feature -- the filter text box and slash command are no longer desired.
Output: Cleaner project_list.py with no filter traces, deleted test_filter.py, updated hint bar text.
</objective>

<execution_context>
@.planning/quick/260417-aeo-remove-filter-text-boxes-and-slash-comma/260417-aeo-PLAN.md
</execution_context>

<context>
@src/joy/widgets/project_list.py
@src/joy/app.py
@tests/test_filter.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove filter functionality from ProjectList widget</name>
  <files>src/joy/widgets/project_list.py</files>
  <action>
In src/joy/widgets/project_list.py, make these specific removals:

1. **Remove the `Input` import from line 13**: Change `from textual.widgets import Input, Static` to `from textual.widgets import Static`

2. **Remove the `NoMatches` import from line 10**: Delete the entire line `from textual.css.query import NoMatches`

3. **Remove the slash binding from BINDINGS list (line 289)**: Delete `Binding("/", "filter", "Filter", show=True),`

4. **Remove the two filter state variables from `__init__` (lines 331-332)**: Delete:
   - `self._filter_active: bool = False`
   - `self._is_filtered: bool = False`

5. **Remove the entire `action_filter` method (lines 652-661)**: The method that mounts the filter Input widget.

6. **Remove the entire `on_input_changed` method (lines 663-673)**: The handler for real-time filtering.

7. **Remove the entire `on_input_submitted` method (lines 675-678)**: The handler for Enter in filter mode.

8. **Remove the entire `on_key` method (lines 680-684)**: The handler for Escape to exit filter mode. IMPORTANT: This entire method only handles the filter escape -- it has no other purpose.

9. **Remove the entire `_exit_filter_mode` method (lines 686-704)**: The helper that removes the filter Input and restores the list.

Do NOT touch any other code. The remaining methods (action_cursor_up, action_cursor_down, action_select_project, action_rename_project, action_delete_project, action_assign_repo, action_new_project, action_archive_project, action_open_archive_browser, sync_to, select_first, select_index, set_projects, _rebuild, _update_highlight, update_badges, action_toggle_status, _get_available_width) must remain intact.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -c "from joy.widgets.project_list import ProjectList; pl = ProjectList; assert not any(b.action == 'filter' for b in pl.BINDINGS); assert not hasattr(pl, 'action_filter') or callable(getattr(pl, 'action_filter', None)) == False; print('OK: no filter binding or method')" && grep -c "filter" src/joy/widgets/project_list.py | xargs -I{} test {} -eq 0 && echo "OK: no filter references remain"</automated>
  </verify>
  <done>ProjectList has zero filter functionality: no slash binding, no filter Input widget, no filter event handlers, no filter state variables. The Input and NoMatches imports are removed.</done>
</task>

<task type="auto">
  <name>Task 2: Update hint bar text and delete test_filter.py</name>
  <files>src/joy/app.py, tests/test_filter.py</files>
  <action>
1. **In src/joy/app.py line 26**, update the project-list hint string to remove "/: Filter":
   - Change: `"n: New  e: Rename  D: Delete  R: Assign repo  /: Filter  a: Archive  A: Archives"`
   - To: `"n: New  e: Rename  D: Delete  R: Assign repo  a: Archive  A: Archives"`
   (Remove "/: Filter  " -- note the two trailing spaces that separate it from the next hint)

2. **Delete the entire file tests/test_filter.py**. This file contains 7 tests that exclusively test the filter feature:
   - test_slash_mounts_filter_input
   - test_filter_realtime
   - test_filter_escape_restores_full_list
   - test_filter_enter_keeps_subset
   - test_filter_clear_restores_list
   - test_filter_double_slash_noop
   - test_filter_case_insensitive

   All 7 tests will fail after Task 1 removes the filter code, so this file must be deleted entirely.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && ! test -f tests/test_filter.py && echo "OK: test_filter.py deleted" && python -c "from joy.app import _PANE_HINTS; assert '/' not in _PANE_HINTS['project-list']; print('OK: no slash in hints')" && uv run pytest tests/ -x --ignore=tests/test_filter.py -q --timeout=30 -m "not slow" 2>&1 | tail -5</automated>
  </verify>
  <done>Hint bar no longer shows "/: Filter". test_filter.py is deleted. All remaining tests pass.</done>
</task>

</tasks>

<verification>
Run the full fast test suite to confirm no regressions:
```bash
cd /Users/pieter/Github/joy && uv run pytest tests/ -x -q --timeout=30 -m "not slow"
```

Verify no filter traces remain in the codebase:
```bash
grep -rn "filter_active\|_is_filtered\|action_filter\|filter-input\|filter_mode" src/joy/widgets/project_list.py
# Should return nothing
```

Verify the slash key is not bound:
```bash
python -c "from joy.widgets.project_list import ProjectList; print([b for b in ProjectList.BINDINGS if '/' in str(b.key)])"
# Should print []
```
</verification>

<success_criteria>
- No filter Input widget, slash binding, filter event handlers, or filter state in project_list.py
- The `Input` and `NoMatches` imports removed from project_list.py
- Hint bar text has no "/: Filter" reference
- tests/test_filter.py file is deleted
- All remaining tests pass (both fast and slow suites unaffected)
- All other ProjectList functionality (cursor nav, new, rename, delete, archive, repo assign, status) works as before
</success_criteria>

<output>
After completion, create `.planning/quick/260417-aeo-remove-filter-text-boxes-and-slash-comma/260417-aeo-SUMMARY.md`
</output>
