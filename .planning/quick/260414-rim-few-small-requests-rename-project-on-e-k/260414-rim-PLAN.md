---
quick: 260414-rim
title: "Few small requests: rename on e, 1-space indent, default branch display, branch filter editor"
tasks: 4
---

<objective>
Four independent UI improvements:
1. Rename project on 'e' key in project list
2. 1-space indent in Project list and Details pane
3. Show default branches as dark grey in Worktree overview instead of filtering them out
4. Editable branch filter list in Settings modal

Each is an atomic commit targeting a distinct feature area.
</objective>

<tasks>

<task id="1">
  <name>Rename project on 'e' key in ProjectList</name>
  <files>
    src/joy/widgets/project_list.py
    src/joy/screens/name_input.py
    tests/test_project_list.py (if exists, add rename test)
  </files>
  <action>
**In `src/joy/widgets/project_list.py`:**

1. Add a new binding to `ProjectList.BINDINGS`:
   ```python
   Binding("e", "rename_project", "Rename", show=True),
   ```

2. Add `action_rename_project` method to `ProjectList`. Pattern follows `action_delete_project`:
   - Guard: if cursor is out of range, return early
   - Get the current `project = self._rows[self._cursor].project`
   - Import `NameInputModal` lazily (same pattern as ConfirmationModal import)
   - Push a `NameInputModal` with a modified title. Since `NameInputModal` currently hardcodes "New Project" as title, we need to make it accept an optional `title` and `initial_value` parameter.
   - In the callback `on_name(name)`:
     - If `name is None`: return (Escape)
     - If `name == project.name`: return (no change)
     - Check for duplicate name: `if any(p.name == name and p is not project for p in self.app._projects)`
       - If duplicate, `self.app.notify(f"Project '{name}' already exists", severity="error", markup=False)` and return
     - Set `project.name = name`
     - Call `self.app._save_projects_bg()` to persist
     - Call `self.set_projects(list(self.app._projects), self._repos)` to re-render the list
     - Restore cursor to the renamed project. Use `call_after_refresh` to find the index of the renamed project and `select_index()` it.
     - `self.app.notify(f"Renamed to: '{name}'", markup=False)`
     - Also re-render the detail pane: `self.app.query_one("#project-detail").set_project(project)`

**In `src/joy/screens/name_input.py`:**

3. Modify `NameInputModal.__init__` to accept optional keyword arguments:
   ```python
   def __init__(self, *, title: str = "New Project", initial_value: str = "", placeholder: str = "Project name") -> None:
       super().__init__()
       self._title = title
       self._initial_value = initial_value
       self._placeholder = placeholder
   ```

4. Update `compose` to use `self._title`, `self._initial_value`, `self._placeholder`:
   ```python
   yield Static(self._title, classes="modal-title")
   yield Input(value=self._initial_value, placeholder=self._placeholder)
   yield Static("Enter to confirm, Escape to cancel", classes="modal-hint")
   ```

5. In `action_rename_project`, push the modal like:
   ```python
   self.app.push_screen(
       NameInputModal(title="Rename Project", initial_value=project.name),
       on_name,
   )
   ```

**Important: TOML key update.** Since `store._projects_to_toml` uses `project.name` as the TOML table key, simply changing `project.name` before calling `_save_projects_bg()` is sufficient -- the old key is gone because the dict is rebuilt fresh from the project list.
  </action>
  <verify>
    Run existing tests: `cd /Users/pieter/Github/joy && uv run python -m pytest tests/ -x -q --ignore=tests/test_tui.py -k "not slow" 2>&1 | tail -20`
    Manual: launch joy, highlight a project, press 'e', type new name, Enter. Project renames in list and detail pane. Escape cancels. Duplicate name is rejected.
  </verify>
  <done>
    - 'e' key opens rename modal pre-filled with current name
    - Enter confirms rename, Escape cancels
    - Duplicate names rejected with error toast
    - TOML file updated with new key
    - Project list and detail pane reflect new name
  </done>
  <commit>feat(project-list): add rename project on e-key</commit>
</task>

<task id="2">
  <name>1-space indent in Project list pane</name>
  <files>
    src/joy/widgets/project_list.py
  </files>
  <action>
**In `src/joy/widgets/project_list.py`:**

The Project list rows (`ProjectRow`) and the Details pane (`ObjectRow`) both use `padding: 0 1` CSS which provides 1-char padding on left and right. The `GroupHeader` widgets also use `padding: 0 1`.

The user wants a 1-space indent. Check current rendering:
- `ProjectRow.__init__` passes `project.name` directly as text content. With `padding: 0 1`, there's already 1 char of left padding from CSS.
- `GroupHeader` also has `padding: 0 1` so repo group headers have 1 char indent too.

This means the CSS `padding: 0 1` is already providing a 1-space indent. Verify visually whether this is sufficient or if the user wants additional indent beyond what padding provides.

Looking at the codebase findings more carefully: the request is "1-space indent in Project and Details panes". The current `padding: 0 1` gives 1 char on each side. If items inside groups should be indented relative to the group header (like in the worktree pane where branches have `" {ICON_BRANCH} "` prefix), then:

1. Change `ProjectRow` to render with a leading space in the text content to indent project names relative to group headers:
   ```python
   super().__init__(f" {project.name}", **kwargs)
   ```
   This gives project names 1 extra space of indent relative to the GroupHeader text, mirroring how worktree rows indent their branch names.

2. Verify that GroupHeader stays at `padding: 0 1` (no extra indent -- it's the section header).

The Details pane (`ObjectRow`) already has `padding: 0 1` and its content is structured in columns (icon | value | kind). The icon column already provides visual indent. Leave Details pane as-is unless the padding needs adjustment. The GroupHeader in project_detail.py also already has `padding: 0 1`.

**Key insight:** The user said "1-space indent in Project and Details panes". The Details pane GroupHeaders and ObjectRows already have consistent `padding: 0 1`. The Project list's ProjectRows also have `padding: 0 1`. The change needed is to add a leading space to ProjectRow content text so items are indented relative to their group headers -- exactly like WorktreeRow does with its branch content.
  </action>
  <verify>
    Manual: launch joy, check that project names in the left pane have a 1-space indent relative to the group header labels.
  </verify>
  <done>
    - Project names in ProjectList show with 1 extra space of indent relative to group headers
    - Visual consistency with WorktreePane indent pattern
  </done>
  <commit>style(project-list): add 1-space indent to project rows</commit>
</task>

<task id="3">
  <name>Show default branches as dark grey in Worktree overview</name>
  <files>
    src/joy/models.py
    src/joy/worktrees.py
    src/joy/widgets/worktree_pane.py
  </files>
  <action>
**In `src/joy/models.py`:**

1. Add `is_default_branch: bool = False` field to `WorktreeInfo` dataclass:
   ```python
   @dataclass
   class WorktreeInfo:
       repo_name: str
       branch: str
       path: str
       is_dirty: bool = False
       has_upstream: bool = True
       is_default_branch: bool = False  # True when branch matches branch_filter
   ```

**In `src/joy/worktrees.py`:**

2. Change `discover_worktrees` to **mark** filtered branches instead of **skipping** them. Replace:
   ```python
   if branch in filter_set:
       continue
   ```
   with:
   ```python
   is_default = branch in filter_set
   ```
   And pass `is_default_branch=is_default` to the `WorktreeInfo` constructor:
   ```python
   results.append(
       WorktreeInfo(
           repo_name=repo.name,
           branch=branch,
           path=path,
           is_dirty=_is_dirty(path),
           has_upstream=_has_upstream(path),
           is_default_branch=is_default,
       )
   )
   ```

**In `src/joy/widgets/worktree_pane.py`:**

3. Update `WorktreeRow.__init__` to accept and store `is_default_branch`:
   - Add `is_default_branch` to the stored attributes: `self.is_default_branch: bool = worktree.is_default_branch`
   - Pass it to `build_content`:
     ```python
     content = self.build_content(
         worktree.branch,
         worktree.is_dirty,
         worktree.has_upstream,
         path,
         mr_info=mr_info,
         is_default_branch=worktree.is_default_branch,
     )
     ```

4. Update `WorktreeRow.build_content` signature to accept `is_default_branch: bool = False`. When `is_default_branch` is True, render the entire row in dim grey style:
   - Use `dim` style for the branch icon and name: `t.append(f" {ICON_BRANCH} ", style="dim")` and `t.append(branch, style="dim")`
   - Skip dirty/upstream indicators for default branches (they're not interesting)
   - Render the path line also in dim: `t.append(f"  {display_path}", style="dim")`
   - When `is_default_branch` is False, keep existing rendering unchanged.

   Specifically, wrap the existing rendering logic:
   ```python
   if is_default_branch:
       t.append(f" {ICON_BRANCH} ", style="dim")
       t.append(branch, style="dim")
       t.append("\n")
       t.append(f"  {display_path}", style="dim")
   else:
       # ... existing code unchanged ...
   ```

5. Update `WorktreePane.set_worktrees`: sorting within each repo group should put default branches at the end (after non-default branches), so active work is always at the top. Change the sort key:
   ```python
   for wt in sorted(grouped[repo_name], key=lambda w: (w.is_default_branch, w.branch.lower())):
   ```
   This sorts non-default (False=0) before default (True=1), then alphabetically within each group.

6. The empty-state message for "No active worktrees" may need updating since worktrees are no longer truly filtered out. If ALL worktrees for all repos are default branches, the pane will show them (dimmed). The "No active worktrees" message now only appears when there are genuinely zero worktrees. The `branch_filter` parameter to `set_worktrees` is no longer needed for the empty-state hint -- simplify or leave as-is for backward compat.

**Test updates:** Update existing worktree tests that rely on branch_filter causing branches to be excluded. They should now expect those branches to be present but marked with `is_default_branch=True`.
  </action>
  <verify>
    Run tests: `cd /Users/pieter/Github/joy && uv run python -m pytest tests/test_worktrees.py tests/test_worktree_pane.py -x -q 2>&1 | tail -20`
    Manual: launch joy, verify that `main` and `testing` branches appear in the worktree list but are rendered in dim/grey style at the bottom of each repo group.
  </verify>
  <done>
    - Default branches (from branch_filter) appear in Worktree pane instead of being hidden
    - Default branches rendered in dim grey with branch icon
    - Default branches sorted to bottom of each repo group
    - Non-default branches render exactly as before
    - WorktreeInfo model includes is_default_branch field
  </done>
  <commit>feat(worktrees): show default branches as dim grey instead of filtering</commit>
</task>

<task id="4">
  <name>Editable branch filter list in Settings modal</name>
  <files>
    src/joy/screens/settings.py
  </files>
  <action>
**In `src/joy/screens/settings.py`:**

1. Create `_BranchFilterRow` (identical pattern to `_RepoRow`):
   ```python
   class _BranchFilterRow(Static):
       """A single branch name row in the branch filter widget."""
       DEFAULT_CSS = """
       _BranchFilterRow { width: 1fr; height: 1; padding: 0 1; }
       """
       def __init__(self, branch_name: str, **kwargs) -> None:
           self.branch_name = branch_name
           super().__init__(branch_name, **kwargs)
   ```

2. Create `_AddBranchRequest` and `_DeleteBranchRequest` messages (same pattern as `_AddRepoRequest` / `_DeleteRepoRequest`):
   ```python
   class _AddBranchRequest(Message):
       """Request to add a new branch filter entry."""

   class _DeleteBranchRequest(Message):
       """Request to delete the selected branch filter entry."""
       def __init__(self, branch_name: str) -> None:
           self.branch_name = branch_name
           super().__init__()
   ```

3. Create `_BranchFilterWidget` (same pattern as `_RepoListWidget`):
   ```python
   class _BranchFilterWidget(VerticalScroll, can_focus=True):
       """Focusable branch filter list with j/k/d/a navigation."""
       BINDINGS = [
           Binding("j", "cursor_down", "Down", show=False),
           Binding("k", "cursor_up", "Up", show=False),
           Binding("down", "cursor_down", "Down"),
           Binding("up", "cursor_up", "Up"),
           Binding("a", "request_add_branch", "Add", show=False),
           Binding("d", "request_delete_branch", "Delete", show=False),
       ]
       DEFAULT_CSS = """
       _BranchFilterWidget { height: auto; max-height: 6; }
       _BranchFilterWidget:focus _BranchFilterRow.--highlight { background: $accent; }
       _BranchFilterRow.--highlight { background: $accent 30%; }
       """
   ```
   With `__init__`, `set_branches(branches: list[str])`, `_update_highlight`, cursor up/down, `selected_branch` property, `action_request_add_branch`, `action_request_delete_branch` -- all mirroring `_RepoListWidget` exactly but using `_BranchFilterRow` and `str` branch names instead of `Repo` objects.

4. In `SettingsModal.compose`, add the branch filter section BEFORE the "Repos" section (or after, placement is flexible -- after Default Open Kinds and before Repos seems natural):
   ```python
   yield Static("Branch Filter", classes="modal-title")
   yield Static(
       "Branches shown dimmed in worktrees. j/k navigate, a to add, d to remove",
       classes="field-label",
   )
   yield _BranchFilterWidget(id="branch-filter-widget")
   ```

5. In `SettingsModal.on_mount`, add:
   ```python
   self.query_one("#branch-filter-widget", _BranchFilterWidget).set_branches(
       self._config.branch_filter
   )
   ```

6. Add message handlers on `SettingsModal` for `_AddBranchRequest` and `_DeleteBranchRequest`:

   `on__add_branch_request`: Push a `NameInputModal` (with `title="Add Branch Filter"`, `placeholder="Branch name (e.g. main)"`) and on result, add to `self._config.branch_filter`, re-render the widget.

   `on__delete_branch_request`: Remove the branch from `self._config.branch_filter`, re-render the widget. No confirmation modal needed for a simple string deletion.

7. Update `_do_save` to include `branch_filter` from the widget state:
   ```python
   branch_widget = self.query_one("#branch-filter-widget", _BranchFilterWidget)
   branch_filter = [row.branch_name for row in branch_widget._rows]
   ```
   Then pass `branch_filter=branch_filter` to the `Config(...)` constructor.

**Important:** The current `_do_save` does NOT pass `branch_filter` to `Config()`, which means it reverts to the default `["main", "testing"]` on every save. This is a latent bug. Fix it by including `branch_filter` from the widget.

Also update `_do_save` to pass `refresh_interval` from config (currently also missing -- verify and fix if so).
  </action>
  <verify>
    Manual: launch joy, press 's' for Settings, scroll to "Branch Filter" section. Verify `main` and `testing` are listed. Navigate with j/k, press 'a' to add a branch, press 'd' to delete one. Save settings. Reopen settings to confirm changes persisted.
    Run tests: `cd /Users/pieter/Github/joy && uv run python -m pytest tests/ -x -q --ignore=tests/test_tui.py -k "not slow" 2>&1 | tail -20`
  </verify>
  <done>
    - Branch Filter section appears in Settings modal
    - Shows current branch_filter entries from config
    - j/k navigation, 'a' to add new branch, 'd' to delete selected
    - Changes persist on Save Settings
    - branch_filter field properly included in _do_save (fixing latent bug)
  </done>
  <commit>feat(settings): add editable branch filter list</commit>
</task>

</tasks>
