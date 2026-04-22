---
phase: 260420-izh-pane-sync-dimmed-selection-and-scoped-op
reviewed: 2026-04-20T00:00:00Z
depth: quick
files_reviewed: 4
files_reviewed_list:
  - src/joy/app.py
  - src/joy/widgets/project_list.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/widgets/worktree_pane.py
findings:
  critical: 0
  warning: 4
  info: 1
  total: 5
status: issues_found
---

# Phase 260420-izh: Code Review Report

**Reviewed:** 2026-04-20
**Depth:** quick (standard-depth analysis applied to all four files)
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the pane sync / dimmed-selection redesign across `app.py`, `project_list.py`, `terminal_pane.py`, and `worktree_pane.py`. The core `sync_to()`/`set_dimmed()` pattern is sound and the `_is_syncing` guard is correctly applied. Four logic bugs found: two CSS specificity issues that make the dim state invisible when the pane has focus, one missing `set_dimmed(False)` clear in the worktree-driven and session-driven sync paths, and one guard bypass through the global `action_open_ide` shortcut.

## Warnings

### WR-01: CSS specificity — `:focus-within` beats `.--dim-selection`; dim is invisible when pane has focus

**File:** `src/joy/widgets/worktree_pane.py:262-276`
**Issue:** `WorktreePane:focus-within WorktreeRow.--highlight` has specificity (0,3,0) — two pseudo-classes/classes on the pane plus one class on the row. `WorktreePane.--dim-selection WorktreeRow.--highlight` has specificity (0,2,0) — one class on the pane plus one on the row. Because the `:focus-within` rule is higher-specificity, focusing the WorktreePane restores the bright `$accent` background on the highlighted row even when `--dim-selection` is active. The dim visual is only visible when the pane does NOT have focus, which is precisely when it matters least (the user cannot trigger an action without first focusing).

The same bug appears in `TerminalPane` at lines 204-224: `TerminalPane:focus-within SessionRow.--highlight` (0,3,0) beats `TerminalPane.--dim-selection SessionRow.--highlight` (0,2,0).

**Fix:** Add a negating selector so the focus-within accent rule does not fire when dimmed:
```css
/* WorktreePane — replace existing :focus-within rule */
WorktreePane:focus-within:not(.--dim-selection) WorktreeRow.--highlight {
    background: $accent;
}
/* TerminalPane — same pattern */
TerminalPane:focus-within:not(.--dim-selection) SessionRow.--highlight {
    background: $accent;
}
```
Adding `:not(.--dim-selection)` raises specificity to (0,4,0) on the normal rule but zeroes it on the dimmed path, keeping `--dim-selection WorktreeRow.--highlight` (0,2,0) uncontested when the class is present.

---

### WR-02: Global `action_open_ide` bypasses `_is_dimmed` guard

**File:** `src/joy/app.py:806-817`
**Issue:** `action_open_ide` (bound globally to `i`) reads `pane._rows[pane._cursor].path` and calls `_open_worktree_path()` with no check against `pane._is_dimmed`. The guard in `WorktreePane.action_activate_row` (line 466-468) correctly blocks `Enter`/`o` when the pane is dimmed, but the global `i` shortcut skips the pane's action entirely and acts directly on whatever worktree row is highlighted — even when it is unrelated to the active project.

```python
# Current code (app.py:814-817) — no dimmed check
if pane._cursor < 0 or not pane._rows or pane._cursor >= len(pane._rows):
    self.notify("No worktree selected", markup=False)
    return
self._open_worktree_path(pane._rows[pane._cursor].path)
```

**Fix:** Add the dimmed check before the cursor validity check:
```python
def action_open_ide(self) -> None:
    from joy.widgets.worktree_pane import WorktreePane as _WorktreePane
    try:
        pane = self.query_one(_WorktreePane)
    except Exception:
        self.notify("Worktrees pane not available", markup=False)
        return
    if pane._is_dimmed:
        self.notify("No worktree for this project", markup=False)
        return
    if pane._cursor < 0 or not pane._rows or pane._cursor >= len(pane._rows):
        self.notify("No worktree selected", markup=False)
        return
    self._open_worktree_path(pane._rows[pane._cursor].path)
```

---

### WR-03: `_sync_from_worktree` never clears dim on WorktreePane when the worktree IS linked

**File:** `src/joy/app.py:556-578`
**Issue:** When the user moves the cursor in `WorktreePane`, `_sync_from_worktree` is called. The method correctly updates `term_pane.set_dimmed(...)` based on whether a matching terminal exists. But it never touches `wt_pane.set_dimmed()` at all. If a previous project-list sync left the WorktreePane dimmed (e.g., the user navigated to a project with no worktrees), and then the user tabs into the WorktreePane and moves the cursor to a valid worktree, the pane remains permanently dimmed — `action_activate_row` will fire the toast "No worktree for this project" even though the user clearly has focus on a valid row.

```python
# _sync_from_worktree (app.py:556-578) — wt_pane.set_dimmed() never called
def _sync_from_worktree(self, worktree: WorktreeInfo) -> None:
    self._is_syncing = True
    try:
        ...
        project = self._rel_index.project_for_worktree(worktree)
        if project is not None:
            self.query_one(ProjectList).sync_to(project.name)
            self.query_one(ProjectDetail).set_project(project)
            terminals = self._rel_index.terminals_for(project)
            if terminals:
                matched = term_pane.sync_to(terminals[0].session_name)
                term_pane.set_dimmed(not matched)
            else:
                term_pane.set_dimmed(True)
        else:
            term_pane.set_dimmed(True)
        # ← wt_pane dim never cleared
```

**Fix:** Clear the WorktreePane's own dim state when the user manually navigates within it:
```python
def _sync_from_worktree(self, worktree: WorktreeInfo) -> None:
    self._is_syncing = True
    try:
        assert self._rel_index is not None
        wt_pane = self.query_one(WorktreePane)
        term_pane = self.query_one(TerminalPane)

        project = self._rel_index.project_for_worktree(worktree)
        if project is not None:
            # User is on a linked worktree — clear dim from WorktreePane
            wt_pane.set_dimmed(False)
            self.query_one(ProjectList).sync_to(project.name)
            self.query_one(ProjectDetail).set_project(project)
            terminals = self._rel_index.terminals_for(project)
            if terminals:
                matched = term_pane.sync_to(terminals[0].session_name)
                term_pane.set_dimmed(not matched)
            else:
                term_pane.set_dimmed(True)
        else:
            # Unlinked worktree — dim both panes that cannot resolve
            wt_pane.set_dimmed(True)
            term_pane.set_dimmed(True)
    finally:
        self._is_syncing = False
```

---

### WR-04: `_sync_from_session` never clears dim on TerminalPane when the session IS linked

**File:** `src/joy/app.py:590-614`
**Issue:** Same structural problem as WR-03 but for `TerminalPane`. When a session highlights and drives sync, `wt_pane.set_dimmed(...)` is correctly updated, but `term_pane.set_dimmed()` is never called. If the TerminalPane was previously dimmed by a project-list sync, it stays dimmed permanently even when the user navigates to a session that resolves to a project. This blocks `action_focus_session` with a misleading toast.

**Fix:** Mirror the WR-03 fix pattern:
```python
def _sync_from_session(self, session_name: str) -> None:
    self._is_syncing = True
    try:
        assert self._rel_index is not None
        wt_pane = self.query_one(WorktreePane)
        term_pane = self.query_one(TerminalPane)

        project = self._rel_index.project_for_terminal(session_name)
        if project is not None:
            # Clear TerminalPane's own dim: user is on a linked session
            term_pane.set_dimmed(False)
            self.query_one(ProjectList).sync_to(project.name)
            self.query_one(ProjectDetail).set_project(project)
            worktrees = self._rel_index.worktrees_for(project)
            if worktrees:
                wt = worktrees[0]
                matched = wt_pane.sync_to(wt.repo_name, wt.branch)
                wt_pane.set_dimmed(not matched)
            else:
                wt_pane.set_dimmed(True)
        else:
            wt_pane.set_dimmed(True)
            term_pane.set_dimmed(True)
    finally:
        self._is_syncing = False
```

## Info

### IN-01: Redundant `_is_syncing = True` inside `_sync_from_*` when caller already sets it

**File:** `src/joy/app.py:525, 562, 596`
**Issue:** `_sync_from_project`, `_sync_from_worktree`, and `_sync_from_session` each set `self._is_syncing = True` at the top of a `try/finally`. However, in the call site for `_sync_from_project` the guard is already set via the same try/finally pattern — but for `_sync_from_worktree` and `_sync_from_session` the caller does NOT pre-set `_is_syncing`; the callers check `if self._is_syncing: return` and then delegate. So the methods correctly own the flag. No bug. But the pattern of setting `_is_syncing = True` inside a private helper is fragile: if any code path calls these helpers without going through the `if self._is_syncing: return` check, the flag will be lost on exception and subsequent sync events will not be suppressed. Consider moving the guard purely to the public event handlers and having the private helpers operate with the invariant that `_is_syncing` is already set.

This is a minor maintainability note, not a current bug.

---

_Reviewed: 2026-04-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick (full file read)_
