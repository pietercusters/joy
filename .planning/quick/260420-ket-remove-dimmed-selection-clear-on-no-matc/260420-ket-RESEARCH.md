# Quick Task 260420-ket: Remove Dimmed-Selection — Research

**Researched:** 2026-04-20
**Domain:** TUI widget cleanup — remove dimmed-selection concept added in quick-260420-izh
**Confidence:** HIGH (full codebase audit, no external dependencies)

## Summary

quick-260420-izh added a "dimmed grey outline" state to WorktreePane and TerminalPane to signal
"no match found during cross-pane sync." This task removes that concept entirely and replaces
it with cursor=-1 (no selection) as the "no match" empty state.

The dimmed concept lives in exactly three files. No tests reference it. The `sync_to()` bool
return introduced in izh is worth keeping — it's still useful for driving `clear_selection()`.
The `set_dimmed(False)` calls that previously cleared dim state will become no-ops (removed
entirely), because clearing selection is done once on `sync_to()` returning False.

**Primary recommendation:** Add `clear_selection()` helper to both panes; replace every
`set_dimmed()` call in app.py with either nothing (when clearing dim on the "source" pane)
or `clear_selection()` (when no match was found in the "target" pane).

---

## Exact Removal List

### `src/joy/widgets/worktree_pane.py`

| What | Lines | Change |
|------|-------|--------|
| `self._is_dimmed: bool = False` | 294 | Remove — `__init__` attribute |
| CSS block `WorktreePane.--dim-selection WorktreeRow.--highlight { ... }` | 272–275 | Remove entire rule |
| CSS block `WorktreePane.--dim-selection:focus-within WorktreeRow.--highlight { ... }` | 277–281 | Remove entire rule |
| `set_dimmed(self, dimmed: bool) -> None:` method | 448–454 | Remove entire method (4 lines + docstring) |
| `if self._is_dimmed:` guard in `action_activate_row` | 471–473 | Remove the guard block (3 lines): `if self._is_dimmed: self.app.notify(...); return` |

**Add:** `clear_selection()` helper method (see Code Examples below).

**Modify:** `action_cursor_up` — handle cursor=-1 entry case.
**Modify:** `action_cursor_down` — handle cursor=-1 entry case.

---

### `src/joy/widgets/terminal_pane.py`

| What | Lines | Change |
|------|-------|--------|
| `self._is_dimmed: bool = False` | 237 | Remove — `__init__` attribute |
| CSS block `TerminalPane.--dim-selection SessionRow.--highlight { ... }` | 220–223 | Remove entire rule |
| CSS block `TerminalPane.--dim-selection:focus-within SessionRow.--highlight { ... }` | 225–229 | Remove entire rule |
| `set_dimmed(self, dimmed: bool) -> None:` method | 392–398 | Remove entire method (4 lines + docstring) |
| `if self._is_dimmed:` guard in `action_focus_session` | 414–416 | Remove the guard block (3 lines): `if self._is_dimmed: self.app.notify(...); return` |

**Add:** `clear_selection()` helper method (see Code Examples below).

**Modify:** `action_cursor_up` — handle cursor=-1 entry case.
**Modify:** `action_cursor_down` — handle cursor=-1 entry case.

---

### `src/joy/app.py`

All `set_dimmed()` call sites. Full map:

#### `_sync_from_project` (lines 518–545)

Current:
```python
if worktrees:
    wt = worktrees[0]
    matched = wt_pane.sync_to(wt.repo_name, wt.branch)
    wt_pane.set_dimmed(not matched)        # <-- REMOVE
else:
    wt_pane.set_dimmed(True)               # <-- REPLACE

if terminals:
    matched = term_pane.sync_to(terminals[0].session_name)
    term_pane.set_dimmed(not matched)      # <-- REMOVE
else:
    term_pane.set_dimmed(True)             # <-- REPLACE
```

New:
```python
if worktrees:
    wt = worktrees[0]
    matched = wt_pane.sync_to(wt.repo_name, wt.branch)
    if not matched:
        wt_pane.clear_selection()          # cursor=-1
else:
    wt_pane.clear_selection()              # no worktrees for this project

if terminals:
    matched = term_pane.sync_to(terminals[0].session_name)
    if not matched:
        term_pane.clear_selection()
else:
    term_pane.clear_selection()
```

#### `_sync_from_worktree` (lines 556–583)

Current:
```python
if project is not None:
    wt_pane.set_dimmed(False)              # <-- REMOVE (no-op needed)
    self.query_one(ProjectList).sync_to(project.name)
    self.query_one(ProjectDetail).set_project(project)
    terminals = self._rel_index.terminals_for(project)
    if terminals:
        matched = term_pane.sync_to(terminals[0].session_name)
        term_pane.set_dimmed(not matched)  # <-- REMOVE/REPLACE
    else:
        term_pane.set_dimmed(True)         # <-- REPLACE
else:
    # Worktree not linked to any project — dim both other panes
    wt_pane.set_dimmed(True)               # <-- REPLACE
    term_pane.set_dimmed(True)             # <-- REPLACE
```

New:
```python
if project is not None:
    # wt_pane: user navigated here directly — selection is already shown, nothing to do
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

#### `_sync_from_session` (lines 594–622)

Current:
```python
if project is not None:
    term_pane.set_dimmed(False)            # <-- REMOVE (no-op needed)
    self.query_one(ProjectList).sync_to(project.name)
    self.query_one(ProjectDetail).set_project(project)
    worktrees = self._rel_index.worktrees_for(project)
    if worktrees:
        wt = worktrees[0]
        matched = wt_pane.sync_to(wt.repo_name, wt.branch)
        wt_pane.set_dimmed(not matched)    # <-- REMOVE/REPLACE
    else:
        wt_pane.set_dimmed(True)           # <-- REPLACE
else:
    # Session not linked to any project — dim both other panes
    term_pane.set_dimmed(True)             # <-- REPLACE
    wt_pane.set_dimmed(True)              # <-- REPLACE
```

New:
```python
if project is not None:
    # term_pane: user navigated here directly — selection is already shown, nothing to do
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

#### `action_open_ide` (lines 814–828)

Current:
```python
if pane._is_dimmed:                        # <-- REMOVE
    self.notify("No worktree for this project", markup=False)
    return
```

New: Remove those 3 lines entirely. The `_cursor < 0` guard immediately below already covers
the "no selection" case — when cursor=-1, `pane._cursor < 0` is True and the existing
`self.notify("No worktree selected")` fires.

#### Docstrings in app.py to update

- `_sync_from_project` docstring line 521: "Calls set_dimmed(True) on panes..." → update to reflect clear_selection
- `_sync_from_worktree` docstring line 559: "Calls set_dimmed(True) on TerminalPane..." → update
- `_sync_from_session` docstring line 597: "Calls set_dimmed(True) on WorktreePane..." → update

---

## Navigation Change: cursor=-1 Entry

### Current behavior

```python
# WorktreePane.action_cursor_up (line 456-459)
def action_cursor_up(self) -> None:
    if self._cursor > 0:        # blocks movement when cursor==0 OR cursor==-1
        self._cursor -= 1
        self._update_highlight()

# WorktreePane.action_cursor_down (line 461-464)
def action_cursor_down(self) -> None:
    if self._cursor < len(self._rows) - 1:  # allows -1 < N-1, so j from -1 goes to -1+1=0... wait
        self._cursor += 1
        self._update_highlight()
```

Wait — re-reading `action_cursor_down`: if `_cursor == -1` and `len(self._rows) == 2`, then
`-1 < 1` is True, so `_cursor` becomes `0`. That already works for j.

For k/up: if `_cursor == -1`, `self._cursor > 0` is False, so pressing k does nothing. That
is acceptable (pressing k when there is no selection does nothing). No change needed.

**Conclusion for down/j:** The existing guard `_cursor < len(self._rows) - 1` naturally handles
cursor=-1 → 0 already. No code change required for action_cursor_down.

**Conclusion for up/k:** Pressing k when cursor=-1 is a no-op. That is the correct behavior
(nowhere to go up to). No change required.

The same analysis applies to TerminalPane — identical guard structure.

**Net result: no changes needed to action_cursor_up or action_cursor_down.** [VERIFIED: reading
the source code directly — line 457 `if self._cursor > 0` blocks at -1, line 462
`if self._cursor < len(self._rows) - 1` passes at -1 when rows exist]

---

## `sync_to()` Bool Return — Keep As-Is

`WorktreePane.sync_to()` (line 430–446) and `TerminalPane.sync_to()` (line 375–390) both
already return `bool`. No changes needed to either method body. The caller in app.py now calls
`clear_selection()` when the return is False instead of calling `set_dimmed(True)`.

---

## `clear_selection()` Helper to Add

Add to both `WorktreePane` and `TerminalPane` (after `sync_to`):

```python
def clear_selection(self) -> None:
    """Clear selection: cursor=-1, remove all --highlight classes."""
    self._cursor = -1
    for r in self._rows:
        r.remove_class("--highlight")
```

This is the canonical implementation from CONTEXT.md specifics section.

---

## Tests

No test files reference `_is_dimmed`, `set_dimmed`, `--dim-selection`, or `clear_selection`.
[VERIFIED: grep over tests/ returned no results]

The existing test `test_enter_noop_when_no_rows` in `test_worktree_pane_cursor.py` already
tests the cursor=-1 no-op path for Enter — it will pass unchanged after this refactor.

The `test_enter_always_opens_ide_even_with_mr` and `test_enter_opens_ide_when_no_mr` tests
test Enter with rows present — they currently call `action_open_ide` via the pane delegate.
After removing the `_is_dimmed` guard from `action_activate_row`, these tests remain green
(the guard removal only affects a code path that was unreachable in those tests anyway).

No new tests are required; no existing tests need modification.

---

## Complete Change Summary (zero residue checklist)

### worktree_pane.py
- [ ] Remove `self._is_dimmed: bool = False` from `__init__`
- [ ] Remove `WorktreePane.--dim-selection WorktreeRow.--highlight { ... }` CSS block
- [ ] Remove `WorktreePane.--dim-selection:focus-within WorktreeRow.--highlight { ... }` CSS block
- [ ] Remove `set_dimmed(self, dimmed: bool) -> None:` method entirely
- [ ] Remove `if self._is_dimmed: ... return` guard from `action_activate_row`
- [ ] Add `clear_selection(self) -> None:` method

### terminal_pane.py
- [ ] Remove `self._is_dimmed: bool = False` from `__init__`
- [ ] Remove `TerminalPane.--dim-selection SessionRow.--highlight { ... }` CSS block
- [ ] Remove `TerminalPane.--dim-selection:focus-within SessionRow.--highlight { ... }` CSS block
- [ ] Remove `set_dimmed(self, dimmed: bool) -> None:` method entirely
- [ ] Remove `if self._is_dimmed: ... return` guard from `action_focus_session`
- [ ] Add `clear_selection(self) -> None:` method

### app.py
- [ ] `_sync_from_project`: replace 4x `set_dimmed()` calls with `clear_selection()` pattern
- [ ] `_sync_from_worktree`: remove 1x `set_dimmed(False)`, replace 3x `set_dimmed(True)` with `clear_selection()`
- [ ] `_sync_from_session`: remove 1x `set_dimmed(False)`, replace 3x `set_dimmed(True)` with `clear_selection()`
- [ ] `action_open_ide`: remove `if pane._is_dimmed: ... return` guard (3 lines)
- [ ] Update docstrings on `_sync_from_project`, `_sync_from_worktree`, `_sync_from_session`

### No changes needed
- `action_cursor_up` / `action_cursor_down` — existing guards already handle cursor=-1 correctly
- `sync_to()` methods — return bool kept, body unchanged
- Test files — zero dimmed references, no test changes needed

---

## Sources

- [VERIFIED: direct file read] `src/joy/widgets/worktree_pane.py` — full audit
- [VERIFIED: direct file read] `src/joy/widgets/terminal_pane.py` — full audit
- [VERIFIED: direct file read] `src/joy/app.py` — full audit of all `set_dimmed` call sites
- [VERIFIED: grep over tests/] — confirmed zero test references to dimmed concept
- [VERIFIED: CONTEXT.md] — `clear_selection()` body specified in `<specifics>` section
