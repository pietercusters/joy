---
phase: quick-260428-gxw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/widgets/project_list.py
  - tests/test_project_list.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Projects are grouped by status (Active, Blocked, Idle) instead of by repo"
    - "Each project row shows its repo name inline (dim, between MR strip and icon ribbon)"
    - "Pressing g (toggle status) re-sorts the entire list and preserves cursor on the same project"
  artifacts:
    - path: "src/joy/widgets/project_list.py"
      provides: "Status-grouped project list with inline repo name"
    - path: "tests/test_project_list.py"
      provides: "Updated tests covering repo name in row content"
  key_links:
    - from: "action_toggle_status"
      to: "set_projects"
      via: "full rebuild instead of single-row re-render"
---

<objective>
Refactor ProjectList from repo-based grouping to status-based grouping, add inline repo name to ProjectRow, and make status toggle trigger a full re-sort with cursor preservation.

Purpose: Status grouping surfaces project priority at a glance. Inline repo name preserves repo context without needing group headers for it.
Output: Updated project_list.py with all three changes, updated tests.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/joy/widgets/project_list.py
@tests/test_project_list.py
@src/joy/models.py (Project dataclass: name, objects, created, repo, status, iterm_tab_id)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add inline repo name to ProjectRow and replace repo grouping with status grouping</name>
  <files>src/joy/widgets/project_list.py</files>
  <action>
Three changes to src/joy/widgets/project_list.py:

**A) Add repo_name parameter to build_content() and render it inline:**

Add `repo_name: str | None = None` parameter to `build_content()` after `agent_count`.

Between the MR strip and the icon ribbon, render the repo name when not None/empty:
- Build a `repo_label = Text()` with `repo_label.append(repo_name, style="dim")` followed by `repo_label.append(" ")` (trailing space separator before ribbon).
- Account for `len(repo_label.plain)` in the `fixed_right` width calculation (add it alongside mr_plain_len, separator, ribbon_width).
- Append `repo_label` text between the MR strip and the ribbon in the final assembly.
- When repo_name is None or empty, do not add repo_label (zero additional width).

**B) Pass repo_name through __init__ and set_counts:**

In `ProjectRow.__init__`: pass `repo_name=project.repo` to `build_content()`.

In `ProjectRow.set_counts()`: pass `repo_name=self.project.repo` to `build_content()`.

**C) Replace repo grouping with status grouping in _rebuild():**

Replace lines 383-416 (the repo grouping logic) with status-based grouping:

```python
# Status group definitions: internal status -> display header
STATUS_ORDER = [
    ("prio", "Active"),
    ("hold", "Blocked"),
    ("idle", "Idle"),
]

# Bucket projects by status
status_buckets: dict[str, list[Project]] = {s: [] for s, _ in STATUS_ORDER}
for p in self._projects:
    bucket = p.status if p.status in status_buckets else "idle"
    status_buckets[bucket].append(p)

# Sort each bucket alphabetically by name
for bucket in status_buckets.values():
    bucket.sort(key=lambda p: p.name.lower())

new_rows: list[ProjectRow] = []
avail_width = self._get_available_width()
first_group = True

for status_key, display_name in STATUS_ORDER:
    projects_in_group = status_buckets[status_key]
    if not projects_in_group:
        continue
    if not first_group:
        scroll.mount(Static("", classes="section-spacer"))
    first_group = False
    scroll.mount(GroupHeader(display_name))
    for p in projects_in_group:
        row = ProjectRow(p, avail_width=avail_width)
        scroll.mount(row)
        new_rows.append(row)
```

The remainder of _rebuild (cursor restoration from line 418 onward) stays unchanged.

Also update the module docstring (line 1) from "repo grouping" to "status grouping".
Update the class docstring for ProjectList to mention status grouping instead of repo grouping.
Update GroupHeader's docstring from "Repo section header" to "Section header for project grouping."

**D) Replace action_toggle_status single-row re-render with full rebuild:**

Replace lines 747-754 (the row-level re-render code after `self.app._save_projects_bg()`) with:
```python
self.set_projects(list(self.app._projects), self._repos)
```

The existing cursor identity restoration in _rebuild() (saved_name matching) handles preserving focus on the toggled project automatically.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run python -m pytest tests/test_project_list.py -x -q</automated>
  </verify>
  <done>
    - build_content accepts repo_name and renders it dim between MR strip and ribbon
    - _rebuild groups by status (Active/Blocked/Idle) not repo
    - action_toggle_status calls set_projects for full re-sort
    - All existing tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Update tests for repo name in ProjectRow</name>
  <files>tests/test_project_list.py</files>
  <action>
Add tests to tests/test_project_list.py:

1. **test_project_row_shows_repo_name_when_set**: Create a Project with `repo="my-repo"`. Call `ProjectRow.build_content(project, 80, mr_info=None, has=has, wt_count=0, agent_count=0, repo_name="my-repo")`. Assert `"my-repo"` appears in `content.plain`. Assert the repo name span has `"dim"` style (use the `_spans_for_icon` helper pattern but searching for "my-repo" substring).

2. **test_project_row_hides_repo_name_when_none**: Create a Project with `repo=None`. Call `build_content` with `repo_name=None`. Assert `content.plain` does NOT contain any extra text between the name padding and the ribbon (i.e., the plain text length is the same as before the refactor for a no-repo project).

3. **test_project_row_constructor_passes_repo**: Create a Project with `repo="test-repo"`. Construct `ProjectRow(project)`. Assert `"test-repo"` appears in `str(row.content)`.

Update `_make_project` helper to accept a `repo: str | None = None` parameter and pass it to `Project(... repo=repo)`.

Verify the existing `test_project_row_shows_project_name` still passes (it uses default repo=None so build_content will get repo_name=None which is the default).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run python -m pytest tests/test_project_list.py -x -v</automated>
  </verify>
  <done>
    - 3 new tests covering repo name display (present, absent, via constructor)
    - All 9+ tests pass (6 existing + 3 new)
    - _make_project helper accepts repo parameter
  </done>
</task>

</tasks>

<verification>
```bash
cd /Users/pieter/Github/joy && uv run python -m pytest tests/test_project_list.py -x -v
```
All tests pass. Manual smoke-test: launch `joy` and confirm projects group under Active/Blocked/Idle headers, repo name shows dim inline, pressing g re-sorts the list.
</verification>

<success_criteria>
- Projects display grouped by status (Active, Blocked, Idle) with section headers
- Empty status groups are not shown
- Each project row shows its repo name dim between MR strip and icon ribbon
- Pressing g cycles status and the project moves to its new group with cursor following it
- All tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260428-gxw-refactor-project-list-status-grouping-in/260428-gxw-SUMMARY.md`
</output>
