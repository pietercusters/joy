---
phase: quick-260422-ksh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/dispatch.py
  - src/joy/widgets/project_detail.py
  - src/joy/widgets/object_row.py
  - src/joy/app.py
autonomous: true
requirements:
  - virtual-row-assembly
  - modular-dispatch
  - repo-keystroke
  - consistent-quick-open
must_haves:
  truths:
    - "TERMINALS row appears in the detail pane when project.iterm_tab_id is set"
    - "Resolver-matched worktree rows appear in the detail pane with no delete action"
    - "r key copies repo name when set, or notifies no repo when unset"
    - "h key creates terminal if missing, activates if present — behavior unchanged"
    - "All quick-open keys (b, m, y, u, t, h, r) route through KindConfig dispatch table"
    - "Adding a new kind requires only updating dispatch.py, not app.py logic"
  artifacts:
    - path: "src/joy/dispatch.py"
      provides: "Per-kind KindConfig dataclass and DISPATCH table"
      exports: ["KindConfig", "DISPATCH"]
    - path: "src/joy/widgets/project_detail.py"
      provides: "Virtual row assembly from objects[], iterm_tab_id, resolver worktrees"
      contains: "_build_virtual_rows"
    - path: "src/joy/app.py"
      provides: "r binding for repo, R for refresh, dispatch-driven quick-open"
      contains: "action_open_repo"
  key_links:
    - from: "src/joy/app.py"
      to: "src/joy/dispatch.py"
      via: "DISPATCH[kind] lookup in _open_first_of_kind"
    - from: "src/joy/widgets/project_detail.py"
      to: "app._rel_index / app._current_worktrees"
      via: "set_project receives resolver_worktrees param"
---

<objective>
Refactor ProjectDetail and keystroke dispatch for unified object view.

Purpose: The detail pane currently shows only stored ObjectItems. Three kinds of
linked objects are invisible: the TERMINALS link (project.iterm_tab_id), the REPO
field (only partially synthesized), and resolver-matched worktrees. Quick-open
shortcuts also have scattered if/else logic that must be hunted through to change.
This refactor adds a virtual row layer and replaces scattered dispatch with a
table-driven KindConfig system.

Output:
- src/joy/dispatch.py (new) — KindConfig dataclass + DISPATCH table
- ProjectDetail updated to synthesize TERMINALS and WORKTREE virtual rows
- app.py quick-open routing replaced with dispatch table; r=repo-copy, R=refresh
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/pieter/Github/joy/.planning/notes/project-detail-virtual-layer-design.md
@/Users/pieter/Github/joy/.planning/todos/pending/refactor-project-detail-unified-object-view.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From src/joy/models.py:
```python
class PresetKind(str, Enum):
    MR = "mr"
    BRANCH = "branch"
    TICKET = "ticket"
    THREAD = "thread"
    FILE = "file"
    NOTE = "note"
    WORKTREE = "worktree"
    TERMINALS = "terminals"
    URL = "url"
    REPO = "repo"

@dataclass
class ObjectItem:
    kind: PresetKind
    value: str
    label: str = ""
    open_by_default: bool = False

@dataclass
class Project:
    name: str
    objects: list[ObjectItem]
    repo: str | None = None
    iterm_tab_id: str | None = None

@dataclass
class WorktreeInfo:
    repo_name: str
    branch: str
    path: str
    is_dirty: bool = False
    has_upstream: bool = True
    is_default_branch: bool = False
```

From src/joy/resolver.py:
```python
class RelationshipIndex:
    def worktrees_for(self, project: Project) -> list[WorktreeInfo]: ...
```

From src/joy/widgets/project_detail.py (current):
```python
class ProjectDetail(Widget, can_focus=True):
    def set_project(self, project: Project) -> None: ...
    def _render_project(self, gen: int = 0, *, initial_cursor: int | None = None) -> None: ...
    # Currently synthesizes REPO row but NOT TERMINALS or resolver worktrees
```

From src/joy/app.py (current):
```python
# r is currently: Binding("r", "action_refresh_worktrees", "Refresh", priority=True)
# R is currently: Binding("R", "action_toggle_auto_refresh", "Auto-refresh", show=False)

def _open_first_of_kind(self, kind: PresetKind) -> None:
    # Looks up first matching item from project.objects
    # Inline if/else: if kind == PresetKind.BRANCH: _copy_branch(item)
    # No support for virtual rows (REPO, TERMINALS)
    # No support for missing-item creation or prompting
```

From src/joy/widgets/object_row.py:
```python
KIND_SHORTCUT: dict[PresetKind, str] = {
    PresetKind.BRANCH: "b",
    PresetKind.MR: "m",
    PresetKind.WORKTREE: "i",
    PresetKind.TICKET: "y",
    PresetKind.NOTE: "u",
    PresetKind.THREAD: "t",
    PresetKind.TERMINALS: "h",
    # REPO: currently missing — needs "r" added
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create dispatch.py and update virtual row assembly in ProjectDetail</name>
  <files>
    src/joy/dispatch.py
    src/joy/widgets/project_detail.py
    src/joy/widgets/object_row.py
  </files>
  <action>
**Step A: Create src/joy/dispatch.py**

Define a `KindConfig` dataclass that captures the 4-state dispatch contract for each
kind, and a `DISPATCH` table mapping `PresetKind` to `KindConfig`.

```python
"""Per-kind dispatch configuration for keystroke actions.

Each PresetKind declares exactly one behavior for each of the four states:
  exists_openable      — kind has a real value and can be opened
  exists_not_openable  — kind has a real value but it is copied, not opened
  missing_auto_create  — kind has no value; one can be created without user input
  missing_needs_input  — kind has no value; user must supply one

Only one of (exists_openable, exists_not_openable) should be True per kind.
Only one of (missing_auto_create, missing_needs_input) should be True per kind;
both may be False if missing is not actionable.

The action strings are method names on JoyApp (without "action_" prefix) that will
be called by the generic dispatcher. The dispatcher resolves which state applies and
calls the appropriate app method.
"""
from __future__ import annotations

from dataclasses import dataclass

from joy.models import PresetKind


@dataclass(frozen=True)
class KindConfig:
    """Dispatch contract for a single PresetKind."""
    exists_openable: bool          # True → call app.action_open_object_of_kind(kind)
    exists_not_openable: bool      # True → call app._copy_first_of_kind(kind)
    missing_auto_create: bool      # True → call app._auto_create_kind(kind)
    missing_needs_input: bool      # True → call app._prompt_for_kind(kind)
    missing_notify: str = ""       # toast when no value and no create/prompt action


# Table-driven dispatch: add/change a kind's behavior here only.
DISPATCH: dict[PresetKind, KindConfig] = {
    PresetKind.MR:        KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.BRANCH:    KindConfig(exists_openable=False, exists_not_openable=True,  missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.TICKET:    KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.NOTE:      KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.THREAD:    KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.FILE:      KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.URL:       KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=True,  missing_notify=""),
    PresetKind.WORKTREE:  KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=False, missing_needs_input=False, missing_notify="No worktree found"),
    PresetKind.TERMINALS: KindConfig(exists_openable=True,  exists_not_openable=False, missing_auto_create=True,  missing_needs_input=False, missing_notify=""),
    PresetKind.REPO:      KindConfig(exists_openable=False, exists_not_openable=True,  missing_auto_create=False, missing_needs_input=False, missing_notify="No repo assigned — press R to assign one"),
}
```

**Step B: Update src/joy/widgets/object_row.py**

Add `PresetKind.REPO: "r"` to `KIND_SHORTCUT`:
```python
KIND_SHORTCUT: dict[PresetKind, str] = {
    PresetKind.BRANCH: "b",
    PresetKind.MR: "m",
    PresetKind.WORKTREE: "i",
    PresetKind.TICKET: "y",
    PresetKind.NOTE: "u",
    PresetKind.THREAD: "t",
    PresetKind.TERMINALS: "h",
    PresetKind.REPO: "r",      # new
}
```

**Step C: Update src/joy/widgets/project_detail.py**

1. Add `resolver_worktrees: list[WorktreeInfo]` parameter to `set_project()` (default `[]`).
   Store as `self._resolver_worktrees`.

2. Extract a new private method `_build_virtual_rows(project) -> dict[PresetKind, list[ObjectItem]]`
   that assembles the `grouped` dict currently built inline in `_render_project`. This method:
   - Starts with all `project.objects` grouped by kind (same as before)
   - Synthesizes REPO row from `project.repo` if set (same as current)
   - NEW: Synthesizes TERMINALS row from `project.iterm_tab_id` if set:
     ```python
     if self._project.iterm_tab_id:
         terminals_item = ObjectItem(kind=PresetKind.TERMINALS, value=self._project.iterm_tab_id, label="")
         grouped.setdefault(PresetKind.TERMINALS, []).append(terminals_item)
     ```
   - NEW: Synthesizes WORKTREE rows from `self._resolver_worktrees` for worktrees NOT already
     in `project.objects` (to avoid duplicates). Mark these as read-only by using a sentinel:
     create a subclass `ReadOnlyObjectItem` or use a flag. Simplest approach: add a module-level
     sentinel set `_READONLY_ITEM_IDS: set[int]` (keyed by `id(item)`) populated in
     `_build_virtual_rows`, cleared on each render.
     
     Implementation of resolver worktree synthesis:
     ```python
     # Paths already stored as WORKTREE objects (avoid duplicates)
     stored_wt_paths: set[str] = {
         obj.value for obj in project.objects if obj.kind == PresetKind.WORKTREE
     }
     for wt in self._resolver_worktrees:
         if wt.path not in stored_wt_paths:
             virt_item = ObjectItem(kind=PresetKind.WORKTREE, value=wt.path, label=wt.branch)
             grouped.setdefault(PresetKind.WORKTREE, []).append(virt_item)
             self._readonly_items.add(id(virt_item))
     ```

3. Add `self._readonly_items: set[int] = set()` to `__init__`.

4. In `_render_project`, clear `self._readonly_items` at the start of each render, then call
   `_build_virtual_rows` instead of the inline grouping logic.

5. Guard delete actions: in `action_delete_object` and `action_force_delete_object`, check
   `id(item) in self._readonly_items`. If True, notify "Worktree rows are read-only" and return
   without deleting.

6. Update `_set_project_with_cursor` to accept and pass through `resolver_worktrees`.

7. The `set_project` signature change needs a note: the resolver worktrees are optional (default
   `[]`) so all existing call sites in app.py remain valid without change. The app.py caller
   can pass them when available (Task 2 will do this).
  </action>
  <verify>
    <automated>/Users/pieter/.nvm/versions/node/v22.17.1/bin/node -e "require('child_process').execSync('cd /Users/pieter/Github/joy && python -m pytest tests/test_object_row.py tests/test_models.py -x -q 2>&1', {stdio: 'inherit'})"</automated>
  </verify>
  <done>
    - src/joy/dispatch.py exists with KindConfig dataclass and DISPATCH table for all 10 PresetKinds
    - KIND_SHORTCUT in object_row.py includes PresetKind.REPO: "r"
    - ProjectDetail synthesizes TERMINALS and resolver WORKTREE virtual rows
    - Virtual WORKTREE rows (from resolver) are blocked from delete with a clear notification
    - Existing tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire dispatch table into app.py quick-open shortcuts and fix r/R key conflict</name>
  <files>src/joy/app.py</files>
  <action>
**Key conflict to resolve first:**
Currently `r` = `action_refresh_worktrees` (priority binding) and `R` = `action_toggle_auto_refresh`
(hidden binding). The design requires `r` = open/copy REPO. Resolution:
- `r` (lowercase) → `action_open_repo` (new, via dispatch)
- `R` (uppercase) → `action_refresh_worktrees` (was priority `r`)
- `action_toggle_auto_refresh` → remove its `R` binding (it was show=False and rarely used;
  can be accessed via settings or dropped entirely since manual refresh via `R` is enough)

**Step A: Update BINDINGS in JoyApp**

Replace:
```python
Binding("r", "refresh_worktrees", "Refresh", priority=True),
...
Binding("R", "toggle_auto_refresh", "Auto-refresh", show=False),
```

With:
```python
Binding("R", "refresh_worktrees", "Refresh", priority=True),
Binding("r", "open_repo", "Repo", show=False),
```

(Remove `toggle_auto_refresh` binding — auto-refresh can still be toggled via its action
but loses the key binding. The method itself stays for future use.)

**Step B: Replace _open_first_of_kind with dispatch-driven implementation**

Import `DISPATCH` from `joy.dispatch` (lazy import inside the method).

New implementation:
```python
def _open_first_of_kind(self, kind: PresetKind) -> None:
    """Dispatch keystroke for *kind* using the DISPATCH table (4-state taxonomy)."""
    from joy.dispatch import DISPATCH  # noqa: PLC0415
    detail = self.query_one(ProjectDetail)
    project = detail._project
    if project is None:
        self.notify("No project selected", markup=False)
        return
    cfg = DISPATCH.get(kind)
    if cfg is None:
        return  # unknown kind — no-op

    # Resolve the value for this kind (check virtual sources too)
    value = self._resolve_kind_value(project, kind)

    if value is not None:
        # Exists path
        if cfg.exists_not_openable:
            self._copy_value_bg(value, kind)
        elif cfg.exists_openable:
            from joy.models import ObjectItem  # noqa: PLC0415
            item = ObjectItem(kind=kind, value=value)
            self._do_open_global(item)
    else:
        # Missing path
        if cfg.missing_auto_create:
            self._auto_create_kind(kind, project)
        elif cfg.missing_needs_input:
            self._prompt_for_kind(kind, project)
        else:
            msg = cfg.missing_notify or f"No {kind.value} found for this project"
            self.notify(msg, markup=False)
```

**Step C: Add `_resolve_kind_value(project, kind) -> str | None`**

Looks up the value for a kind across all virtual sources (not just `project.objects`):
```python
def _resolve_kind_value(self, project: Project, kind: PresetKind) -> str | None:
    """Return the first value for *kind* from any source (objects, repo, iterm_tab_id)."""
    if kind == PresetKind.REPO:
        return project.repo  # direct field
    if kind == PresetKind.TERMINALS:
        return project.iterm_tab_id  # direct field
    # Resolver worktrees: return path of first matched worktree for WORKTREE kind
    if kind == PresetKind.WORKTREE:
        if self._rel_index is not None:
            worktrees = self._rel_index.worktrees_for(project)
            if worktrees:
                return worktrees[0].path
        # Fall through to objects[] (stored WORKTREE items)
    return next((obj.value for obj in project.objects if obj.kind == kind), None)
```

**Step D: Add `_copy_value_bg(value, kind)` worker**

Replaces the existing `_copy_branch` method with a generic version:
```python
@work(thread=True, exit_on_error=False)
def _copy_value_bg(self, value: str, kind: PresetKind) -> None:
    """Copy a string value to clipboard via pbcopy."""
    import subprocess as _subprocess  # noqa: PLC0415
    try:
        _subprocess.run(["pbcopy"], input=value.encode("utf-8"), check=True)
        self.notify(f"Copied {kind.value}: {value}", markup=False)
    except Exception as exc:
        self.notify(f"Failed to copy: {exc}", severity="error", markup=False)
```

Keep `_copy_branch` as a thin wrapper calling `_copy_value_bg` for backward compat, OR remove it
if it is only called from `action_open_branch` (which is being replaced). It is safe to remove
`_copy_branch` since `_open_first_of_kind` was the only caller and is now replaced.

**Step E: Add `_auto_create_kind(kind, project)` and `_prompt_for_kind(kind, project)`**

`_auto_create_kind` covers the TERMINALS auto-create case (currently in `action_open_terminal`):
```python
def _auto_create_kind(self, kind: PresetKind, project: Project) -> None:
    """Handle missing_auto_create: create the resource without user input."""
    if kind == PresetKind.TERMINALS:
        if project.name not in self._tabs_creating:
            self._tabs_creating.add(project.name)
            self._do_create_tab_for_project(project)
    # Future kinds: add elif here
```

`_prompt_for_kind` handles missing_needs_input (user must supply URL/path):
```python
def _prompt_for_kind(self, kind: PresetKind, project: Project) -> None:
    """Handle missing_needs_input: push a ValueInputModal for the user to supply the value."""
    from joy.screens import ValueInputModal  # noqa: PLC0415

    def on_value(value: str | None) -> None:
        if value is None:
            return
        from joy.models import ObjectItem  # noqa: PLC0415
        obj = ObjectItem(kind=kind, value=value)
        project.objects.append(obj)
        self._save_projects_bg()
        self.query_one(ProjectDetail).set_project(project)
        self.notify(f"Added: {kind.value} '{_truncate(value)}'", markup=False)

    self.push_screen(ValueInputModal(kind), on_value)
```

**Step F: Add `action_open_repo` and update `action_open_terminal`**

```python
def action_open_repo(self) -> None:
    """r key: copy repo name or notify no repo (REPO dispatch)."""
    self._open_first_of_kind(PresetKind.REPO)
```

Simplify `action_open_terminal` to delegate to the dispatch:
```python
def action_open_terminal(self) -> None:
    """h key: open/create terminal via dispatch table."""
    self._open_first_of_kind(PresetKind.TERMINALS)
```

The dispatch for TERMINALS: `exists_openable=True` → calls `_do_open_global` with an
ObjectItem(TERMINALS, tab_id). BUT `open_object` for ITERM type uses the old iterm2 Python
API which is not the current approach. The current `action_open_terminal` calls
`_do_activate_tab(project.iterm_tab_id)` which is the correct tab-ID based activation.

To keep correct behavior, add a special case in `_open_first_of_kind` for TERMINALS when
a value exists: call `_do_activate_tab(value)` instead of `_do_open_global`. Override
via a `special_open` field in KindConfig or just check `kind == PresetKind.TERMINALS` after
the dispatch lookup:
```python
    if value is not None:
        if cfg.exists_not_openable:
            self._copy_value_bg(value, kind)
        elif cfg.exists_openable:
            # TERMINALS: use tab activation instead of open_object
            if kind == PresetKind.TERMINALS:
                self._do_activate_tab(value)
            else:
                from joy.models import ObjectItem  # noqa: PLC0415
                item = ObjectItem(kind=kind, value=value)
                self._do_open_global(item)
```

**Step G: Pass resolver worktrees to ProjectDetail**

In `on_project_list_project_highlighted` and `on_project_list_project_selected` and any
other place that calls `detail.set_project(project)`, pass resolver worktrees:
```python
resolver_wts = self._rel_index.worktrees_for(project) if self._rel_index else []
detail.set_project(project, resolver_worktrees=resolver_wts)
```

Locations to update in app.py (grep for `.set_project(`):
- `on_project_list_project_highlighted`
- `on_project_list_project_selected`
- `_propagate_changes` (after propagation rebuild)
- `_sync_from_worktree`
- `_sync_from_session`
- `_start_add_object_loop` (on_value callback)
- `action_new_project` (on_result callback)
- `_start_add_object_loop` inner on_value

**Step H: Update HintBar hint for project-detail**

In `_PANE_HINTS`, update the detail hint to include `r`:
```python
"project-detail": "o: Open  n: Add  e: Edit  d: Delete  D: Force del  space: Toggle  r: Repo",
```

Also update the refresh key hint bar for any pane that shows `r` as Refresh (currently
the hint bar doesn't show global bindings, so this mainly affects the Footer display).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && /Users/pieter/.nvm/versions/node/v22.17.1/bin/node -e "require('child_process').execSync('python -m pytest tests/ -x -q --ignore=tests/test_tui.py 2>&1', {stdio: 'inherit'})"</automated>
  </verify>
  <done>
    - r key triggers action_open_repo → copies repo name via clipboard if set; notifies "No repo assigned" if not set
    - R key triggers refresh (was r)
    - h key behavior unchanged: activates existing terminal tab, creates one if missing
    - All quick-open keys (b, m, i, y, u, t, h, r) route through _open_first_of_kind with DISPATCH table
    - _open_first_of_kind has no PresetKind-specific if/else except the TERMINALS tab-activation special case
    - _prompt_for_kind is called for missing items that need user input (MR, BRANCH, TICKET, NOTE, THREAD, FILE, URL)
    - Resolver worktrees passed to ProjectDetail.set_project() at all call sites
    - Unit tests pass (excluding slow TUI tests)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user keypress → dispatch | User keystroke triggers action; dispatch table must not execute wrong action for a kind |
| clipboard write | `pbcopy` receives value from project data — project data is trusted (user-entered), no sanitization needed |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ksh-01 | Tampering | `_readonly_items` sentinel set | accept | Set is keyed by object `id()` (memory address), cleared on each render; no persistence path, no cross-user concern for single-user TUI |
| T-ksh-02 | Elevation of Privilege | `_prompt_for_kind` adds arbitrary ObjectItem | accept | Value comes from user's own modal input; only adds to their own project; single-user tool |
| T-ksh-03 | Spoofing | TERMINALS tab_id passed to `_do_activate_tab` | accept | tab_id sourced from iTerm2 API on load; no external injection path |
</threat_model>

<verification>
Run full fast test suite (excluding slow TUI tests):
```
cd /Users/pieter/Github/joy && python -m pytest tests/ -q --ignore=tests/test_tui.py
```

Manual spot-checks:
1. Launch joy, select a project with a repo set → press r → clipboard should contain repo name
2. Select a project with no repo → press r → toast "No repo assigned — press R to assign one"
3. Press R (shift+r) → worktrees refresh triggers (same behavior as old r)
4. Project with iterm_tab_id → TERMINALS row appears in detail pane
5. Select that project, h key → activates the tab
6. Detail pane with resolver-matched worktree → WORKTREE row appears without delete action (d key shows "Worktree rows are read-only")
</verification>

<success_criteria>
- dispatch.py exists with KindConfig and DISPATCH covering all 10 PresetKinds
- ProjectDetail._build_virtual_rows synthesizes REPO, TERMINALS, and resolver WORKTREE rows
- Resolver WORKTREE rows cannot be deleted (read-only guard)
- r → repo copy, R → refresh (key swap complete, no regression on refresh)
- All quick-open keys route through _open_first_of_kind + DISPATCH
- Fast test suite passes (tests/ excluding test_tui.py)
</success_criteria>

<output>
After completion, create `.planning/quick/260422-ksh-refactor-projectdetail-and-keystroke-dis/260422-ksh-SUMMARY.md`
</output>
