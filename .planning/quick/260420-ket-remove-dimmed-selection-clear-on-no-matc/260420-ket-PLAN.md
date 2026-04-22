---
phase: quick-260420-ket
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/widgets/worktree_pane.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/app.py
autonomous: true
requirements:
  - Remove dimmed-selection concept from quick-260420-izh
  - Replace set_dimmed() with clear_selection() (cursor=-1, no highlight) on no-match

must_haves:
  truths:
    - "When project sync finds no matching worktree, the worktree pane shows no highlighted row (cursor=-1)"
    - "When project sync finds no matching terminal, the terminal pane shows no highlighted row (cursor=-1)"
    - "Unlinked worktree row is navigable and openable with normal yellow accent — no dim styling"
    - "Unlinked terminal session is navigable and focusable — no dim styling"
    - "Pressing Enter on a pane with cursor=-1 is a silent no-op (existing _cursor<0 guard)"
    - "No _is_dimmed, set_dimmed(), or --dim-selection references remain anywhere in the codebase"
  artifacts:
    - path: "src/joy/widgets/worktree_pane.py"
      provides: "WorktreePane with clear_selection() method, no set_dimmed/--dim-selection"
    - path: "src/joy/widgets/terminal_pane.py"
      provides: "TerminalPane with clear_selection() method, no set_dimmed/--dim-selection"
    - path: "src/joy/app.py"
      provides: "_sync_from_* methods using clear_selection(), action_open_ide without _is_dimmed guard"
  key_links:
    - from: "app.py:_sync_from_project"
      to: "WorktreePane.clear_selection / TerminalPane.clear_selection"
      via: "called when sync_to() returns False or no items in rel_index"
    - from: "app.py:action_open_ide"
      to: "WorktreePane._cursor"
      via: "pane._cursor < 0 guard (existing) replaces removed _is_dimmed guard"
---

<objective>
Remove the dimmed-selection concept added in quick-260420-izh entirely. Replace every
`set_dimmed()` call with `clear_selection()` (cursor=-1, all --highlight removed). Unlinked
items are fully selectable and openable. No grey outline, no muted CSS, no toast guards.

Purpose: "No selection" is a cleaner empty state than "dimmed selection" — less visual noise,
         no special mode for the user to learn or get stuck in.
Output:  Three modified files. Zero `_is_dimmed`, `set_dimmed`, or `--dim-selection` references.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/pieter/Github/joy/.planning/STATE.md
@/Users/pieter/Github/joy/.planning/quick/260420-ket-remove-dimmed-selection-clear-on-no-matc/260420-ket-CONTEXT.md
@/Users/pieter/Github/joy/.planning/quick/260420-ket-remove-dimmed-selection-clear-on-no-matc/260420-ket-RESEARCH.md

<interfaces>
<!-- Key interfaces the executor needs. Verified from live source. -->

From src/joy/widgets/worktree_pane.py:
```python
# Lines to REMOVE from WorktreePane.__init__ (line 294):
self._is_dimmed: bool = False

# CSS blocks to REMOVE (lines 272-281):
# WorktreePane.--dim-selection WorktreeRow.--highlight { ... }
# WorktreePane.--dim-selection:focus-within WorktreeRow.--highlight { ... }

# Method to REMOVE entirely (lines 448-454):
def set_dimmed(self, dimmed: bool) -> None: ...

# Guard block to REMOVE from action_activate_row (lines 471-473):
if self._is_dimmed:
    self.app.notify("No worktree for this project", markup=False)
    return

# Method to ADD (after sync_to, around line 447):
def clear_selection(self) -> None:
    """Clear selection: cursor=-1, remove all --highlight classes."""
    self._cursor = -1
    for r in self._rows:
        r.remove_class("--highlight")
```

From src/joy/widgets/terminal_pane.py:
```python
# Lines to REMOVE from TerminalPane.__init__ (line 237):
self._is_dimmed: bool = False

# CSS blocks to REMOVE (lines 220-229):
# TerminalPane.--dim-selection SessionRow.--highlight { ... }
# TerminalPane.--dim-selection:focus-within SessionRow.--highlight { ... }

# Method to REMOVE entirely (lines 392-398):
def set_dimmed(self, dimmed: bool) -> None: ...

# Guard block to REMOVE from action_focus_session (lines 414-416):
if self._is_dimmed:
    self.app.notify("No terminal for this project", markup=False)
    return

# Method to ADD (after sync_to, around line 391):
def clear_selection(self) -> None:
    """Clear selection: cursor=-1, remove all --highlight classes."""
    self._cursor = -1
    for r in self._rows:
        r.remove_class("--highlight")
```

From src/joy/app.py (verified live):
```python
# _sync_from_project (lines 518-545): 4x set_dimmed calls
# _sync_from_worktree (lines 556-583): 1x set_dimmed(False) + 3x set_dimmed(True)
# _sync_from_session (lines 594-622): 1x set_dimmed(False) + 3x set_dimmed(True)
# action_open_ide (lines 822-824): _is_dimmed guard block
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove dimmed API from WorktreePane and TerminalPane, add clear_selection()</name>
  <files>src/joy/widgets/worktree_pane.py, src/joy/widgets/terminal_pane.py</files>
  <action>
**worktree_pane.py — make these exact changes:**

1. In DEFAULT_CSS (around lines 272-281), remove the two CSS blocks:
   - `WorktreePane.--dim-selection WorktreeRow.--highlight { background: transparent; color: $text-muted; text-style: dim; }`
   - `WorktreePane.--dim-selection:focus-within WorktreeRow.--highlight { background: transparent; color: $text-muted; text-style: dim; }`

2. In `__init__` (line 294), remove:
   `self._is_dimmed: bool = False`

3. Remove the entire `set_dimmed()` method (lines 448-454):
   ```python
   def set_dimmed(self, dimmed: bool) -> None:
       """Set dimmed selection state (no project match). Adds/removes --dim-selection CSS class."""
       self._is_dimmed = dimmed
       if dimmed:
           self.add_class("--dim-selection")
       else:
           self.remove_class("--dim-selection")
   ```

4. Add `clear_selection()` method immediately after `sync_to()` ends (before `action_cursor_up`):
   ```python
   def clear_selection(self) -> None:
       """Clear selection: cursor=-1, remove all --highlight classes."""
       self._cursor = -1
       for r in self._rows:
           r.remove_class("--highlight")
   ```

5. In `action_activate_row()` (lines 469-476), remove the `_is_dimmed` guard block:
   ```python
   # REMOVE these 3 lines:
   if self._is_dimmed:
       self.app.notify("No worktree for this project", markup=False)
       return
   ```
   Leave the `if self._cursor < 0 or ...` guard and `self.app.action_open_ide()` intact.

---

**terminal_pane.py — make these exact changes:**

1. In DEFAULT_CSS (around lines 220-229), remove the two CSS blocks:
   - `TerminalPane.--dim-selection SessionRow.--highlight { background: transparent; color: $text-muted; text-style: dim; }`
   - `TerminalPane.--dim-selection:focus-within SessionRow.--highlight { background: transparent; color: $text-muted; text-style: dim; }`

2. In `__init__` (line 237), remove:
   `self._is_dimmed: bool = False`

3. Remove the entire `set_dimmed()` method (lines 392-398):
   ```python
   def set_dimmed(self, dimmed: bool) -> None:
       """Set dimmed selection state (no project match). Adds/removes --dim-selection CSS class."""
       self._is_dimmed = dimmed
       if dimmed:
           self.add_class("--dim-selection")
       else:
           self.remove_class("--dim-selection")
   ```

4. Add `clear_selection()` method immediately after `sync_to()` ends (before `action_cursor_up`):
   ```python
   def clear_selection(self) -> None:
       """Clear selection: cursor=-1, remove all --highlight classes."""
       self._cursor = -1
       for r in self._rows:
           r.remove_class("--highlight")
   ```

5. In `action_focus_session()` (lines 412-420), remove the `_is_dimmed` guard block:
   ```python
   # REMOVE these 3 lines:
   if self._is_dimmed:
       self.app.notify("No terminal for this project", markup=False)
       return
   ```
   Leave the `if self._cursor < 0 or ...` guard and `self._do_activate(session_id)` intact.

Do NOT change `action_cursor_up`, `action_cursor_down`, or `sync_to()` — they are correct as-is.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && /Users/pieter/.nvm/versions/node/v22.17.1/bin/node -e "const {execSync} = require('child_process'); const r = execSync('grep -rn "_is_dimmed\\|set_dimmed\\|--dim-selection" src/joy/widgets/worktree_pane.py src/joy/widgets/terminal_pane.py 2>&1 || true').toString(); if(r.trim()) { console.error('FAIL: dimmed residue found:\n' + r); process.exit(1); } else { console.log('PASS: no dimmed references in panes'); }" && grep -n "clear_selection" src/joy/widgets/worktree_pane.py src/joy/widgets/terminal_pane.py</automated>
  </verify>
  <done>
    - Zero occurrences of `_is_dimmed`, `set_dimmed`, `--dim-selection` in worktree_pane.py and terminal_pane.py
    - `clear_selection()` defined in both panes with correct body (cursor=-1, remove --highlight loop)
    - `action_activate_row` in WorktreePane has no `_is_dimmed` guard
    - `action_focus_session` in TerminalPane has no `_is_dimmed` guard
  </done>
</task>

<task type="auto">
  <name>Task 2: Update app.py — replace set_dimmed() calls with clear_selection(), remove _is_dimmed guard</name>
  <files>src/joy/app.py</files>
  <action>
Make four targeted edits to app.py:

**Edit 1 — `_sync_from_project` (lines 518-545): Replace 4 set_dimmed calls**

Replace the method body (everything inside the try block) from:
```python
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
```

To:
```python
worktrees = self._rel_index.worktrees_for(project)
if worktrees:
    wt = worktrees[0]
    matched = wt_pane.sync_to(wt.repo_name, wt.branch)
    if not matched:
        wt_pane.clear_selection()
else:
    wt_pane.clear_selection()

terminals = self._rel_index.terminals_for(project)
if terminals:
    matched = term_pane.sync_to(terminals[0].session_name)
    if not matched:
        term_pane.clear_selection()
else:
    term_pane.clear_selection()
```

Also update the docstring on `_sync_from_project`: replace "Calls set_dimmed(True) on panes that cannot match the active project." with "Calls clear_selection() on panes that cannot match the active project."

**Edit 2 — `_sync_from_worktree` (lines 556-583): Remove set_dimmed(False), replace 3x set_dimmed(True)**

Replace the method body (everything inside the try block) from:
```python
project = self._rel_index.project_for_worktree(worktree)
if project is not None:
    wt_pane.set_dimmed(False)  # User navigated here — worktree is active
    self.query_one(ProjectList).sync_to(project.name)
    self.query_one(ProjectDetail).set_project(project)
    terminals = self._rel_index.terminals_for(project)
    if terminals:
        matched = term_pane.sync_to(terminals[0].session_name)
        term_pane.set_dimmed(not matched)
    else:
        term_pane.set_dimmed(True)  # No terminals for this project
else:
    # Worktree not linked to any project — dim both other panes
    wt_pane.set_dimmed(True)
    term_pane.set_dimmed(True)
```

To:
```python
project = self._rel_index.project_for_worktree(worktree)
if project is not None:
    self.query_one(ProjectList).sync_to(project.name)
    self.query_one(ProjectDetail).set_project(project)
    terminals = self._rel_index.terminals_for(project)
    if terminals:
        matched = term_pane.sync_to(terminals[0].session_name)
        if not matched:
            term_pane.clear_selection()
    else:
        term_pane.clear_selection()
else:
    # Worktree not linked to any project — clear both other panes
    wt_pane.clear_selection()
    term_pane.clear_selection()
```

Also update the docstring on `_sync_from_worktree`: replace "Calls set_dimmed(True) on TerminalPane when no terminal matches the project.\n        Clears dim on WorktreePane (user navigated to it directly — it's now active)." with "Calls clear_selection() on TerminalPane when no terminal matches the project."

**Edit 3 — `_sync_from_session` (lines 594-622): Remove set_dimmed(False), replace 3x set_dimmed(True)**

Replace the method body (everything inside the try block) from:
```python
project = self._rel_index.project_for_terminal(session_name)
if project is not None:
    term_pane.set_dimmed(False)  # User navigated here — session is active
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
    # Session not linked to any project — dim both other panes
    term_pane.set_dimmed(True)
    wt_pane.set_dimmed(True)
```

To:
```python
project = self._rel_index.project_for_terminal(session_name)
if project is not None:
    self.query_one(ProjectList).sync_to(project.name)
    self.query_one(ProjectDetail).set_project(project)
    worktrees = self._rel_index.worktrees_for(project)
    if worktrees:
        wt = worktrees[0]
        matched = wt_pane.sync_to(wt.repo_name, wt.branch)
        if not matched:
            wt_pane.clear_selection()
    else:
        wt_pane.clear_selection()
else:
    # Session not linked to any project — clear both other panes
    term_pane.clear_selection()
    wt_pane.clear_selection()
```

Also update the docstring on `_sync_from_session`: replace "Calls set_dimmed(True) on WorktreePane when no worktree matches the project.\n        Clears dim on TerminalPane (user navigated to it directly — it's now active)." with "Calls clear_selection() on WorktreePane when no worktree matches the project."

**Edit 4 — `action_open_ide` (lines 822-824): Remove the `_is_dimmed` guard block**

Remove these 3 lines entirely:
```python
if pane._is_dimmed:
    self.notify("No worktree for this project", markup=False)
    return
```

The existing `if pane._cursor < 0 or not pane._rows or pane._cursor >= len(pane._rows):` guard immediately below handles the no-selection case (cursor=-1 is already < 0).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && grep -n "_is_dimmed\|set_dimmed\|--dim-selection" src/joy/app.py || echo "PASS: no dimmed references in app.py"</automated>
  </verify>
  <done>
    - Zero occurrences of `_is_dimmed`, `set_dimmed`, or `--dim-selection` in app.py
    - All three `_sync_from_*` methods use `clear_selection()` where `set_dimmed(True)` was, no `set_dimmed(False)` calls remain
    - `action_open_ide` has no `_is_dimmed` check — only the `_cursor < 0` guard remains
    - Docstrings on all three `_sync_from_*` methods no longer mention set_dimmed
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify zero residue and run tests</name>
  <files></files>
  <action>
Run a codebase-wide grep to confirm zero residue of the dimmed concept across all source files:

```bash
grep -rn "_is_dimmed\|set_dimmed\|--dim-selection" src/ tests/ 2>/dev/null || echo "PASS: zero dimmed residue"
```

Then run the fast test suite to confirm no regressions:

```bash
cd /Users/pieter/Github/joy && python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20
```

If tests fail, read the failure output and fix the root cause before marking done. Expected: all fast tests pass (slow tests excluded by default per pytest.ini).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && grep -rn "_is_dimmed\|set_dimmed\|--dim-selection" src/ tests/ 2>/dev/null; echo "exit:$?"; python -m pytest tests/ -x -q --tb=short 2>&1 | tail -10</automated>
  </verify>
  <done>
    - grep over src/ and tests/ returns zero matches for `_is_dimmed`, `set_dimmed`, `--dim-selection`
    - pytest fast suite passes with no failures
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| n/a | This task is a pure internal refactor — no trust boundaries change. No new inputs, no new outputs, no new external surfaces. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ket-01 | Tampering | WorktreePane.action_activate_row | accept | Removing the _is_dimmed guard leaves only the _cursor<0 guard — already correct. No new attack surface. |
</threat_model>

<verification>
Full verification checklist:

1. `grep -rn "_is_dimmed\|set_dimmed\|--dim-selection" src/ tests/` → zero results
2. `clear_selection()` exists in both `WorktreePane` and `TerminalPane`
3. `_sync_from_project`, `_sync_from_worktree`, `_sync_from_session` in app.py use `clear_selection()` on no-match paths
4. `action_open_ide` in app.py has no `_is_dimmed` check
5. `pytest tests/ -x -q` passes
</verification>

<success_criteria>
- No `_is_dimmed`, `set_dimmed`, or `--dim-selection` anywhere in the codebase
- `clear_selection()` available on WorktreePane and TerminalPane
- Sync logic in app.py drives `clear_selection()` on no-match (not a dimmed style)
- All existing fast tests pass
- Unlinked items are fully openable (no toast guard blocks them)
</success_criteria>

<output>
After completion, create `.planning/quick/260420-ket-remove-dimmed-selection-clear-on-no-matc/260420-ket-SUMMARY.md`
</output>
