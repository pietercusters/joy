---
phase: quick-260420-izh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/widgets/worktree_pane.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/widgets/project_list.py
  - src/joy/app.py
autonomous: true
requirements:
  - SYNC-01
  - SYNC-02
  - SYNC-03
  - SYNC-04
  - SYNC-05
  - SYNC-06

must_haves:
  truths:
    - "When a project is selected and has no worktrees, WorktreePane shows a dimmed border outline (no fill) on its highlighted row"
    - "When a project is selected and has no terminals, TerminalPane shows a dimmed border outline (no fill) on its highlighted row"
    - "Pressing Enter/o in a dimmed WorktreePane shows 'No worktree for this project' toast instead of opening"
    - "Pressing Enter/o in a dimmed TerminalPane shows 'No terminal for this project' toast instead of opening"
    - "Selecting from WorktreePane or TerminalPane also drives dimmed state on the other panes that cannot match"
    - "When a sync succeeds (pane finds a match), the dimmed state is cleared — normal yellow fill restores"
  artifacts:
    - path: "src/joy/widgets/worktree_pane.py"
      provides: "sync_to() returns bool; _is_dimmed attr; set_dimmed() method; --dim-selection CSS; action_activate_row guard"
    - path: "src/joy/widgets/terminal_pane.py"
      provides: "sync_to() returns bool; _is_dimmed attr; set_dimmed() method; --dim-selection CSS; action_focus_session guard"
    - path: "src/joy/widgets/project_list.py"
      provides: "sync_to() returns bool (uniform pattern)"
    - path: "src/joy/app.py"
      provides: "_sync_from_project/_sync_from_worktree/_sync_from_session read bool returns and call set_dimmed()"
  key_links:
    - from: "app.py _sync_from_project"
      to: "WorktreePane.set_dimmed / TerminalPane.set_dimmed"
      via: "bool return from sync_to()"
      pattern: "wt_matched = .*sync_to.*; .*set_dimmed\\(not wt_matched\\)"
    - from: "WorktreePane.action_activate_row"
      to: "self.app.notify"
      via: "_is_dimmed guard"
      pattern: "if self._is_dimmed"
    - from: "TerminalPane.action_focus_session"
      to: "self.app.notify"
      via: "_is_dimmed guard"
      pattern: "if self._is_dimmed"
---

<objective>
Redesign cross-pane sync to add a "dimmed" state for panes that cannot match the active selection.

Purpose: Currently if a project has no worktrees or terminals, the other panes silently leave their cursor unchanged with no visual feedback. The new behavior gives users clear signal: the pane highlights its row with a muted border outline (not the yellow accent fill), and any attempt to open an item shows an informative status toast instead of silently failing.

Output: Four modified files. sync_to() returns bool on all three panes. WorktreePane and TerminalPane gain _is_dimmed state, set_dimmed() method, CSS for the dimmed look, and guards in their open actions. app.py's three _sync_from_* methods read the return values and set dimmed state accordingly.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/pieter/Github/joy/.planning/STATE.md
@/Users/pieter/Github/joy/.planning/quick/260420-izh-pane-sync-dimmed-selection-and-scoped-op/260420-izh-CONTEXT.md
@/Users/pieter/Github/joy/.planning/quick/260420-izh-pane-sync-dimmed-selection-and-scoped-op/260420-izh-RESEARCH.md

<interfaces>
<!-- Key code as it exists in the codebase before changes. -->

From src/joy/widgets/worktree_pane.py — WorktreePane:
```python
# __init__ sets:
self._cursor: int = -1
self._rows: list[WorktreeRow] = []

# Current sync_to — returns None, silent:
def sync_to(self, repo_name: str, branch: str) -> None:
    for i, row in enumerate(self._rows):
        if row.repo_name == repo_name and row.branch == branch:
            self._cursor = i
            for r in self._rows: r.remove_class("--highlight")
            row.add_class("--highlight")
            row.scroll_visible()
            return
    # No match: _cursor unchanged

# Current action — no guard:
def action_activate_row(self) -> None:
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    self.app.action_open_ide()

# Existing CSS in DEFAULT_CSS:
# WorktreePane:focus-within WorktreeRow.--highlight { background: $accent; }
# WorktreeRow.--highlight { background: $accent 30%; }
# WorktreeRow.--unlinked { color: $text-muted; text-style: dim; }
```

From src/joy/widgets/terminal_pane.py — TerminalPane:
```python
# __init__ sets:
self._cursor: int = -1
self._rows: list[SessionRow] = []

# Current sync_to — returns None, silent:
def sync_to(self, session_name: str) -> None:
    for i, row in enumerate(self._rows):
        if row.session_name == session_name:
            self._cursor = i
            for r in self._rows: r.remove_class("--highlight")
            row.add_class("--highlight")
            row.scroll_visible()
            return

# Current action — no guard:
def action_focus_session(self) -> None:
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    session_id = self._rows[self._cursor].session_id
    self._do_activate(session_id)

# Existing CSS in DEFAULT_CSS:
# TerminalPane:focus-within SessionRow.--highlight { background: $accent; }
# SessionRow.--highlight { background: $accent 30%; }
```

From src/joy/widgets/project_list.py — ProjectList:
```python
# Current sync_to — returns None:
def sync_to(self, project_name: str) -> None:
    for i, row in enumerate(self._rows):
        if row.project.name == project_name:
            self._cursor = i
            for r in self._rows: r.remove_class("--highlight")
            row.add_class("--highlight")
            row.scroll_visible()
            return
```

From src/joy/app.py — sync methods (lines 518–583):
```python
def _sync_from_project(self, project: Project) -> None:
    self._is_syncing = True
    try:
        assert self._rel_index is not None
        worktrees = self._rel_index.worktrees_for(project)
        if worktrees:
            wt = worktrees[0]
            self.query_one(WorktreePane).sync_to(wt.repo_name, wt.branch)
        terminals = self._rel_index.terminals_for(project)
        if terminals:
            self.query_one(TerminalPane).sync_to(terminals[0].session_name)
    finally:
        self._is_syncing = False

def _sync_from_worktree(self, worktree: WorktreeInfo) -> None:
    self._is_syncing = True
    try:
        assert self._rel_index is not None
        project = self._rel_index.project_for_worktree(worktree)
        if project is not None:
            self.query_one(ProjectList).sync_to(project.name)
            self.query_one(ProjectDetail).set_project(project)
            terminals = self._rel_index.terminals_for(project)
            if terminals:
                self.query_one(TerminalPane).sync_to(terminals[0].session_name)
    finally:
        self._is_syncing = False

def _sync_from_session(self, session_name: str) -> None:
    self._is_syncing = True
    try:
        assert self._rel_index is not None
        project = self._rel_index.project_for_terminal(session_name)
        if project is not None:
            self.query_one(ProjectList).sync_to(project.name)
            self.query_one(ProjectDetail).set_project(project)
            worktrees = self._rel_index.worktrees_for(project)
            if worktrees:
                wt = worktrees[0]
                self.query_one(WorktreePane).sync_to(wt.repo_name, wt.branch)
    finally:
        self._is_syncing = False
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add bool returns and dimmed state to WorktreePane, TerminalPane, ProjectList</name>
  <files>
    src/joy/widgets/worktree_pane.py
    src/joy/widgets/terminal_pane.py
    src/joy/widgets/project_list.py
  </files>
  <action>
**worktree_pane.py**

1. In `WorktreePane.__init__`, add after `self._rows: list[WorktreeRow] = []`:
   ```python
   self._is_dimmed: bool = False
   ```

2. Change `sync_to()` return type from `-> None` to `-> bool`. Add `return True` in the found branch (before the existing `return`). Add `return False` at the end (replacing the comment). Full replacement:
   ```python
   def sync_to(self, repo_name: str, branch: str) -> bool:
       """Move cursor to matching (repo_name, branch) row without posting WorktreeHighlighted.

       Silent cursor mutation for cross-pane sync. Does NOT call .focus(). (D-09, D-10)
       Returns True if a match was found, False otherwise. (D-08)
       """
       for i, row in enumerate(self._rows):
           if row.repo_name == repo_name and row.branch == branch:
               self._cursor = i
               # Inline highlight-only path: CSS + scroll, no post_message (Pitfall 1)
               for r in self._rows:
                   r.remove_class("--highlight")
               row.add_class("--highlight")
               row.scroll_visible()
               return True
       # No match: leave _cursor unchanged (D-08)
       return False
   ```

3. Add `set_dimmed()` method after `sync_to()`:
   ```python
   def set_dimmed(self, dimmed: bool) -> None:
       """Set dimmed selection state (no project match). Adds/removes --dim-selection CSS class."""
       self._is_dimmed = dimmed
       if dimmed:
           self.add_class("--dim-selection")
       else:
           self.remove_class("--dim-selection")
   ```

4. In `action_activate_row()`, add dimmed guard at the top (before the cursor bounds check):
   ```python
   def action_activate_row(self) -> None:
       """Open the highlighted worktree in the IDE (Enter key — delegates to app)."""
       if self._is_dimmed:
           self.app.notify("No worktree for this project", markup=False)
           return
       if self._cursor < 0 or self._cursor >= len(self._rows):
           return
       self.app.action_open_ide()
   ```

5. In `DEFAULT_CSS`, add dimmed CSS rules inside the `WorktreePane { ... }` block — add after the `WorktreeRow.--unlinked` rule:
   ```tcss
   WorktreePane.--dim-selection WorktreeRow.--highlight {
       background: transparent;
       color: $text-muted;
       text-style: dim;
   }
   ```

---

**terminal_pane.py**

1. In `TerminalPane.__init__`, add after `self._rows: list[SessionRow] = []`:
   ```python
   self._is_dimmed: bool = False
   ```

2. Change `sync_to()` return type from `-> None` to `-> bool`. Full replacement:
   ```python
   def sync_to(self, session_name: str) -> bool:
       """Move cursor to matching session_name row without posting SessionHighlighted.

       Silent cursor mutation for cross-pane sync. Does NOT call .focus(). (D-09, D-10)
       Returns True if a match was found, False otherwise. (D-08)
       """
       for i, row in enumerate(self._rows):
           if row.session_name == session_name:
               self._cursor = i
               for r in self._rows:
                   r.remove_class("--highlight")
               row.add_class("--highlight")
               row.scroll_visible()
               return True
       # No match: leave _cursor unchanged (D-08)
       return False
   ```

3. Add `set_dimmed()` method after `sync_to()`:
   ```python
   def set_dimmed(self, dimmed: bool) -> None:
       """Set dimmed selection state (no project match). Adds/removes --dim-selection CSS class."""
       self._is_dimmed = dimmed
       if dimmed:
           self.add_class("--dim-selection")
       else:
           self.remove_class("--dim-selection")
   ```

4. In `action_focus_session()`, add dimmed guard at the top:
   ```python
   def action_focus_session(self) -> None:
       """Activate the highlighted session (D-12). No-op if cursor is invalid."""
       if self._is_dimmed:
           self.app.notify("No terminal for this project", markup=False)
           return
       if self._cursor < 0 or self._cursor >= len(self._rows):
           return
       session_id = self._rows[self._cursor].session_id
       self._do_activate(session_id)
   ```

5. In `DEFAULT_CSS`, add dimmed CSS rules after the `TerminalPane .section-spacer` rule:
   ```tcss
   TerminalPane.--dim-selection SessionRow.--highlight {
       background: transparent;
       color: $text-muted;
       text-style: dim;
   }
   ```

---

**project_list.py**

Change `sync_to()` return type from `-> None` to `-> bool` for uniform pattern. Add `return True` in found branch, `return False` at end. Update docstring to note the return value.
  </action>
  <verify>
    <automated>/Users/pieter/.nvm/versions/node/v22.17.1/bin/node --version && cd /Users/pieter/Github/joy && python -m pytest tests/ -x -q --ignore=tests/tui 2>&1 | head -40</automated>
  </verify>
  <done>
    - WorktreePane.sync_to() returns bool (True on match, False on no match)
    - TerminalPane.sync_to() returns bool (True on match, False on no match)
    - ProjectList.sync_to() returns bool (True on match, False on no match)
    - WorktreePane._is_dimmed: bool = False in __init__; set_dimmed() method present
    - TerminalPane._is_dimmed: bool = False in __init__; set_dimmed() method present
    - action_activate_row() and action_focus_session() both guard on _is_dimmed and show notify toast
    - --dim-selection CSS class added to both pane DEFAULT_CSS blocks
    - All existing tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Update app.py sync methods to read bool returns and set dimmed state</name>
  <files>
    src/joy/app.py
  </files>
  <action>
Replace the three `_sync_from_*` methods in app.py. All three follow the same pattern: read the bool return from `sync_to()` and call `set_dimmed()` accordingly.

**Replace `_sync_from_project()` (lines 518–534):**
```python
def _sync_from_project(self, project: Project) -> None:
    """Drive WorktreePane and TerminalPane to first items related to project. (D-04)

    Calls set_dimmed(True) on panes that cannot match the active project.
    Called with _is_syncing guard. Uses try/finally to always clear the guard.
    """
    self._is_syncing = True
    try:
        assert self._rel_index is not None
        wt_pane = self.query_one(WorktreePane)
        term_pane = self.query_one(TerminalPane)

        worktrees = self._rel_index.worktrees_for(project)
        if worktrees:
            wt = worktrees[0]
            matched = wt_pane.sync_to(wt.repo_name, wt.branch)
            wt_pane.set_dimmed(not matched)
        else:
            wt_pane.set_dimmed(True)  # No worktrees for this project

        terminals = self._rel_index.terminals_for(project)
        if terminals:
            matched = term_pane.sync_to(terminals[0].session_name)
            term_pane.set_dimmed(not matched)
        else:
            term_pane.set_dimmed(True)  # No terminals for this project
    finally:
        self._is_syncing = False
```

**Replace `_sync_from_worktree()` (lines 545–558):**
```python
def _sync_from_worktree(self, worktree: WorktreeInfo) -> None:
    """Drive ProjectList and TerminalPane based on a highlighted worktree. (D-05)

    Calls set_dimmed(True) on TerminalPane when no terminal matches the project.
    """
    self._is_syncing = True
    try:
        assert self._rel_index is not None
        term_pane = self.query_one(TerminalPane)
        project = self._rel_index.project_for_worktree(worktree)
        if project is not None:
            self.query_one(ProjectList).sync_to(project.name)
            self.query_one(ProjectDetail).set_project(project)
            terminals = self._rel_index.terminals_for(project)
            if terminals:
                matched = term_pane.sync_to(terminals[0].session_name)
                term_pane.set_dimmed(not matched)
            else:
                term_pane.set_dimmed(True)  # No terminals for this project
        else:
            # Worktree not linked to any project — dim TerminalPane
            term_pane.set_dimmed(True)
    finally:
        self._is_syncing = False
```

**Replace `_sync_from_session()` (lines 569–583):**
```python
def _sync_from_session(self, session_name: str) -> None:
    """Drive ProjectList and WorktreePane based on a highlighted terminal session. (D-06)

    Calls set_dimmed(True) on WorktreePane when no worktree matches the project.
    """
    self._is_syncing = True
    try:
        assert self._rel_index is not None
        wt_pane = self.query_one(WorktreePane)
        project = self._rel_index.project_for_terminal(session_name)
        if project is not None:
            self.query_one(ProjectList).sync_to(project.name)
            self.query_one(ProjectDetail).set_project(project)
            worktrees = self._rel_index.worktrees_for(project)
            if worktrees:
                wt = worktrees[0]
                matched = wt_pane.sync_to(wt.repo_name, wt.branch)
                wt_pane.set_dimmed(not matched)
            else:
                wt_pane.set_dimmed(True)  # No worktrees for this project
        else:
            # Session not linked to any project — dim WorktreePane
            wt_pane.set_dimmed(True)
    finally:
        self._is_syncing = False
```

No other changes to app.py are needed. The `_is_syncing` guard and `on_*_highlighted` handlers are unchanged. `set_dimmed()` only adds/removes a CSS class — it is safe to call inside the `_is_syncing = True` block (no messages posted, no loop risk).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -m pytest tests/ -x -q --ignore=tests/tui 2>&1 | tail -20</automated>
  </verify>
  <done>
    - _sync_from_project() calls set_dimmed() on both WorktreePane and TerminalPane based on sync_to() return
    - _sync_from_worktree() calls set_dimmed() on TerminalPane based on sync_to() return (or True when no project)
    - _sync_from_session() calls set_dimmed() on WorktreePane based on sync_to() return (or True when no project)
    - All existing unit tests still pass
    - No regressions in sync loop guard behavior (the _is_syncing pattern is unchanged)
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pane state → UI | _is_dimmed flag drives CSS class addition and notify calls — all within the TUI, no external I/O |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-izh-01 | Tampering | set_dimmed() | accept | Method is internal; only called from app.py _sync_from_* methods within _is_syncing guard. No external input path. |
| T-izh-02 | Denial of Service | notify() in dimmed pane actions | accept | notify() is Textual built-in with no user-controlled content; message string is hardcoded. No amplification risk. |
</threat_model>

<verification>
After both tasks complete:

1. Run full unit test suite (excluding slow TUI tests):
   ```
   cd /Users/pieter/Github/joy && python -m pytest tests/ -x -q --ignore=tests/tui
   ```
   All tests must pass.

2. Manual smoke test (via `uv run joy` or `uv tool run joy`):
   - Select a project with no worktrees → WorktreePane row shows muted/dim highlight (not yellow fill)
   - Press Enter/o in that dimmed WorktreePane → toast "No worktree for this project" appears
   - Select a project with no terminals → TerminalPane row shows muted/dim highlight
   - Press Enter in that dimmed TerminalPane → toast "No terminal for this project" appears
   - Select a project WITH worktrees → WorktreePane highlight restores to yellow accent fill
</verification>

<success_criteria>
- sync_to() on WorktreePane, TerminalPane, ProjectList all return bool
- WorktreePane and TerminalPane have _is_dimmed attribute and set_dimmed() method
- --dim-selection CSS class on pane causes highlighted row to render with transparent background + muted/dim text (not yellow accent fill)
- Pressing Enter/o on a dimmed pane shows "No X for this project" toast and returns early
- app.py reads bool returns from sync_to() and calls set_dimmed() in all three _sync_from_* methods
- All existing unit tests pass with no regressions
</success_criteria>

<output>
After completion, create `.planning/quick/260420-izh-pane-sync-dimmed-selection-and-scoped-op/260420-izh-SUMMARY.md`
</output>
