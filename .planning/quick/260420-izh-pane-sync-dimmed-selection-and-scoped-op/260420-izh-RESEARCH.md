# Quick Task 260420-izh: Pane Sync — Dimmed Selection + Scoped Open

**Researched:** 2026-04-20
**Domain:** Textual TUI cross-pane sync, CSS selection states, key binding guards
**Confidence:** HIGH — all findings from direct codebase inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Dimmed state: **border outline only**, muted/grey, no fill color
- Scoped-open behavior: **show brief status message** ("No X for this project") instead of silently ignoring
- Multi-match rule: **first item in list** (topmost) that belongs to the project
- Last-action-wins: selecting in any pane re-drives all others

### Claude's Discretion
- Exact "source of truth" mechanics (last-action-wins is the natural model)
- How to detect project membership per item type (use existing project linkage data)
- Dimmed border CSS/TCSS class implementation details
- Whether to centralize sync logic or use distributed watchers — choose cleanest
</user_constraints>

---

## Summary

The current pane sync works via three message handlers in `app.py` (`on_project_list_project_highlighted`, `on_worktree_pane_worktree_highlighted`, `on_terminal_pane_session_highlighted`). Each calls a private `_sync_from_*` method that drives the other panes via their `sync_to()` methods. A boolean `_is_syncing` guard prevents infinite loops.

The new behavior adds a third state to each pane call: instead of either "found and synced" or "not found, cursor unchanged", the pane must distinguish **matched** (sync succeeded) vs **unmatched** (no item for this project). Unmatched panes display a dimmed border-outline selection style. Key actions in unmatched panes show a status toast instead of executing.

**Primary recommendation:** Modify `sync_to()` in WorktreePane and TerminalPane to return `bool` (matched or not), then have app.py add/remove a CSS class `--dim-selection` based on that return value. Guard key actions with a `_is_dimmed` attribute on each pane.

---

## 1. Current Sync Architecture (Exact Code Locations)

### Message Flow

**Source panes post messages; app.py handles them:**

| Source | Message Class | Handler in app.py | Lines |
|--------|--------------|-------------------|-------|
| `ProjectList` | `ProjectHighlighted` | `on_project_list_project_highlighted` | app.py:508–516 |
| `WorktreePane` | `WorktreeHighlighted` | `on_worktree_pane_worktree_highlighted` | app.py:536–543 |
| `TerminalPane` | `SessionHighlighted` | `on_terminal_pane_session_highlighted` | app.py:560–567 |

**Message is fired in `_update_highlight()`**, which is called from cursor movement actions. Each pane checks `getattr(self.app, "_is_syncing", False)` before posting to prevent loops.

### sync_to() — current signature (returns None, silent)

| Widget | Method | Key arg | Behaviour when no match |
|--------|--------|---------|-------------------------|
| `ProjectList` | `sync_to(project_name: str)` | project name | `_cursor` unchanged |
| `WorktreePane` | `sync_to(repo_name: str, branch: str)` | repo+branch | `_cursor` unchanged |
| `TerminalPane` | `sync_to(session_name: str)` | session name | `_cursor` unchanged |

**Key gap:** None of these return anything. App has no signal about whether a sync target was found.

### Guard mechanism (`_is_syncing`)

`app._is_syncing: bool` is set before calling `sync_to()`, cleared in `finally`. `_update_highlight()` checks it before posting messages. This is the correct pattern to keep — the new feature extends on top of it.

### RelationshipIndex — what's available

`resolver.py:RelationshipIndex` provides:
- `worktrees_for(project) -> list[WorktreeInfo]` — all worktrees linked to a project
- `terminals_for(project) -> list[TerminalSession]` — all sessions linked to a project
- `project_for_worktree(wt) -> Project | None` — inverse lookup
- `project_for_terminal(session_name) -> Project | None` — inverse lookup

This is the correct source of truth for "does pane X have anything for this project?" No new data structures needed.

### ProjectDetail — always syncs (no concept of "no match")

`ProjectDetail.set_project(project)` always succeeds — it simply renders whatever project it's given. Rule 1 (exact item match) and Rule 2 (project match) are both trivially satisfied for the detail pane because it IS the project display. **ProjectDetail never enters dimmed state** — it always reflects the active project. This simplifies the design significantly.

---

## 2. What Needs to Change

### 2a. `sync_to()` must return `bool`

Each pane's `sync_to()` already knows whether it found a match (the `return` in the found branch vs the comment at the end of the no-match branch). Change to return `True` on match, `False` on no match.

**WorktreePane.sync_to** — `worktree_pane.py:419–434`
**TerminalPane.sync_to** — `terminal_pane.py:364–378`
**ProjectList.sync_to** — `project_list.py:664–682`

### 2b. App-side: read return value and set dimmed state

In `_sync_from_project()` (app.py:518–534):
```python
wt_matched = self.query_one(WorktreePane).sync_to(wt.repo_name, wt.branch)
term_matched = self.query_one(TerminalPane).sync_to(terminals[0].session_name)
```

If `wt_matched` is `False` (no worktrees for this project), call `worktree_pane.set_dimmed(True)`.
If `term_matched` is `False`, call `terminal_pane.set_dimmed(True)`.

Same pattern applies in `_sync_from_worktree()` and `_sync_from_session()`.

### 2c. Dimmed state on panes

Add `_is_dimmed: bool = False` attribute to `WorktreePane` and `TerminalPane`. Add a `set_dimmed(state: bool)` method that:
1. Stores `self._is_dimmed = state`
2. Calls `self.add_class("--dim-selection")` or `self.remove_class("--dim-selection")`

### 2d. CSS for dimmed state

The `--dim-selection` class needs to apply a visible-but-muted highlight to the cursor row. The dimmed cursor row must not use `$accent` background (that's the "active" highlight). Instead, use a grey border outline on the currently-highlighted row.

The cleanest approach in Textual TCSS:

```tcss
/* In the pane's DEFAULT_CSS or app CSS */
WorktreePane.--dim-selection WorktreeRow.--highlight {
    background: transparent;
    border-left: thick $text-muted 50%;
}
TerminalPane.--dim-selection SessionRow.--highlight {
    background: transparent;
    border-left: thick $text-muted 50%;
}
```

This coexists cleanly with the existing `.--highlight` rules:
```tcss
/* Existing — unchanged */
WorktreePane:focus-within WorktreeRow.--highlight { background: $accent; }
WorktreeRow.--highlight { background: $accent 30%; }
```

When the pane has `--dim-selection`, the more-specific `WorktreePane.--dim-selection WorktreeRow.--highlight` rule wins over the base `WorktreeRow.--highlight` rule, overriding the fill with transparent + a left border indicator.

**Alternative:** Use `color: $text-muted` + `text-style: dim` instead of border-left if border-left renders oddly. Row height for `WorktreeRow` is `height: 2` so a left border is visible.

### 2e. Guard key actions (scoped-open behavior)

When a pane is dimmed and user presses a key to open something (Enter/o in WorktreePane, Enter/o/h in TerminalPane), the action should show a toast instead.

**Pattern:** In each action handler, check `self._is_dimmed` first:

```python
def action_activate_row(self) -> None:  # WorktreePane
    if self._is_dimmed:
        self.app.notify("No worktree for this project", markup=False)
        return
    # ... existing logic
```

For TerminalPane `action_focus_session`:
```python
def action_focus_session(self) -> None:
    if self._is_dimmed:
        self.app.notify("No terminal for this project", markup=False)
        return
    # ... existing logic
```

The global bindings in app.py (`action_open_ide`, `action_open_terminal`, etc.) already route through the pane's `_cursor` — they don't need separate guarding since the pane action handles it.

---

## 3. Sync Logic After Redesign

The key insight: **every sync source must declare dimmed state for all panes it didn't match**.

### `_sync_from_project(project)` — triggered when project list cursor moves

```python
def _sync_from_project(self, project: Project) -> None:
    self._is_syncing = True
    try:
        wt_pane = self.query_one(WorktreePane)
        term_pane = self.query_one(TerminalPane)

        worktrees = self._rel_index.worktrees_for(project)
        if worktrees:
            matched = wt_pane.sync_to(worktrees[0].repo_name, worktrees[0].branch)
            wt_pane.set_dimmed(not matched)
        else:
            wt_pane.set_dimmed(True)  # no worktrees for this project

        terminals = self._rel_index.terminals_for(project)
        if terminals:
            matched = term_pane.sync_to(terminals[0].session_name)
            term_pane.set_dimmed(not matched)
        else:
            term_pane.set_dimmed(True)  # no terminals for this project

    finally:
        self._is_syncing = False
```

### `_sync_from_worktree(worktree)` — triggered when worktree pane cursor moves

```python
def _sync_from_worktree(self, worktree: WorktreeInfo) -> None:
    self._is_syncing = True
    try:
        project = self._rel_index.project_for_worktree(worktree)
        term_pane = self.query_one(TerminalPane)
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
            # Worktree not linked to any project — dim TerminalPane too
            term_pane.set_dimmed(True)
    finally:
        self._is_syncing = False
```

Same pattern applies to `_sync_from_session`.

### When to clear dimmed state

- Call `set_dimmed(False)` on a pane when `sync_to()` returns `True` (successful match).
- Also clear on initial data load (after `set_worktrees` / `set_sessions` completes), since the first sync will re-evaluate.
- The `_is_syncing = True` guard during `_set_worktrees` / `_set_terminal_sessions` already suppresses sync during data rebuild — dimmed state is re-evaluated on the next user navigation event.

---

## 4. Edge Cases

### No `_rel_index` yet (before first data load completes)

The existing check `if self._sync_enabled and self._rel_index is not None` in each handler already gates all sync operations. When `_rel_index` is None, no sync runs, so no dimmed state is set. Both panes start with `_is_dimmed = False`, which is correct (no false "no match" toasts before data loads).

### Worktree not linked to any project

`project_for_worktree()` returns `None`. This already causes the `if project is not None:` block to be skipped. With the new design, we also dim TerminalPane in this case (since there's no project context to find a terminal for).

### ProjectList `sync_to()` return value

`ProjectList.sync_to()` should also return `bool`, though the current callers don't always need it. Making it consistent is low-cost and makes the pattern uniform.

### CSS specificity in Textual TCSS

Textual TCSS specificity works similarly to web CSS. The rule `WorktreePane.--dim-selection WorktreeRow.--highlight` has higher specificity than the bare `WorktreeRow.--highlight` rule, so it will correctly override. Verified: Textual supports compound selectors (parent.class child.class). [ASSUMED — based on Textual CSS documentation knowledge; verify against Textual 8.x TCSS if behavior is unexpected]

---

## 5. Files to Modify

| File | What Changes |
|------|-------------|
| `src/joy/widgets/worktree_pane.py` | `sync_to()` returns `bool`; add `_is_dimmed`, `set_dimmed()`; add CSS for `--dim-selection`; guard `action_activate_row` |
| `src/joy/widgets/terminal_pane.py` | `sync_to()` returns `bool`; add `_is_dimmed`, `set_dimmed()`; add CSS for `--dim-selection`; guard `action_focus_session` |
| `src/joy/widgets/project_list.py` | `sync_to()` returns `bool` (for uniformity; callers don't currently need it) |
| `src/joy/app.py` | `_sync_from_project()`, `_sync_from_worktree()`, `_sync_from_session()` — read return values and call `set_dimmed()` |

**Not touched:** `project_detail.py` (always matches), `resolver.py` (no change needed), `models.py`, `store.py`.

---

## 6. Common Pitfalls

### Pitfall 1: Dimmed state not cleared when project re-links

If user adds a worktree object to a project, `_rel_index` is only recomputed on the next background refresh cycle. The dimmed state will persist until then. This is acceptable — the user can press `r` to force refresh.

### Pitfall 2: `set_dimmed()` called during `_is_syncing` guard

`set_dimmed()` only adds/removes a CSS class — it does not post messages or move cursors, so calling it inside the `_is_syncing = True` block is safe. No loop risk.

### Pitfall 3: Empty pane + dimmed state

If WorktreePane has no rows at all (`_rows == []`), `sync_to()` returns `False` → `set_dimmed(True)`. The empty state message ("No active worktrees") is still shown. The `--dim-selection` class on the pane has no effect (no rows to highlight), so no visual conflict. The guard in `action_activate_row` fires and shows the toast instead.

### Pitfall 4: CSS override not working

If the compound selector `WorktreePane.--dim-selection WorktreeRow.--highlight` doesn't override the background set by `WorktreeRow.--highlight`, add `!important` to the background property in the dim rule, or restructure as a single rule that covers both cases. Textual 8.x does support TCSS `!important`. [ASSUMED on specificity behavior — test visually]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Textual TCSS compound selector `ParentWidget.--class ChildWidget.--class` has higher specificity than bare `ChildWidget.--class` | Section 4, CSS specificity | Dim highlight doesn't override yellow fill; fix: add `!important` or inline style |
| A2 | Adding/removing CSS class on widget triggers immediate visual refresh without needing `refresh()` call | Section 2c | Dimmed state not visible until next render cycle; fix: call `self.refresh()` after class change |

---

## Sources

- `src/joy/app.py` — full sync architecture, `_sync_from_*` methods, `_is_syncing` guard
- `src/joy/widgets/project_list.py` — `ProjectList.sync_to()`, `ProjectHighlighted` message, CSS classes
- `src/joy/widgets/worktree_pane.py` — `WorktreePane.sync_to()`, `WorktreeHighlighted` message, CSS classes, `--unlinked` pattern (precedent for non-active row styling)
- `src/joy/widgets/terminal_pane.py` — `TerminalPane.sync_to()`, `SessionHighlighted` message, action guards
- `src/joy/resolver.py` — `RelationshipIndex` API: `worktrees_for()`, `terminals_for()`, inverse lookups
- `.planning/quick/260420-izh-pane-sync-dimmed-selection-and-scoped-op/260420-izh-CONTEXT.md` — locked decisions
