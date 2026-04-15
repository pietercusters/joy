# Quick Task 260415-gw0: Keyboard Shortcuts Rethink — Research

**Researched:** 2026-04-15
**Domain:** Textual key bindings, custom footer widget, pane-aware hint bar
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Global shortcuts (pop-up/notify if data missing):**
- b — copy branch to clipboard
- m — open MR
- i — open worktree in IDE
- y — open ticket
- u — open note
- t — open thread
- h — open terminal/agent
- R — toggle auto-refresh
- Unchanged: O (open all defaults), s (settings), r (refresh worktrees), l (legend), q (quit), x (sync toggle), Tab, Escape

**Pane-specific shortcuts (ProjectDetail/objects pane only):**
- e — edit selected entry
- n — add new item
- d — delete with confirmation prompt
- D — force delete without confirmation
- o — open selected item
- Unchanged: j/k, arrows, Enter, /, R

**Remove altogether:**
- a — replaced by n

**Two rows of keyboard hints at bottom:**
- Row 1: pane-specific shortcuts for the focused pane
- Row 2: global shortcuts
- Do NOT hint: j/k, arrows, Enter, Escape, Tab

**Hint label format:** verbose: `key: Full label`
- Global row example: `[global]  R: Auto-refresh  s: Settings  r: Refresh  l: Legend  q: Quit`

**Worktrees pane focused:** first row empty/hidden

**Terminal pane scope:** `e` for rename only; NO n/d/D in TerminalPane

### Claude's Discretion

- Implementation approach for two-row footer (custom widget vs Textual Footer extension)
- How to handle 'b' global shortcut when no branch context exists (use existing notify system)
- Exact labels for hint display (keep them concise but clear)

### Deferred Ideas (OUT OF SCOPE)

None listed.
</user_constraints>

---

## Summary

This task has three distinct work areas: (1) binding reorganization across five files, (2) a custom two-row hint bar widget replacing the standard `Footer`, and (3) new global shortcut actions in `JoyApp` that find and open objects by type. The codebase is well-structured for this change: `on_descendant_focus` in `JoyApp` already detects which pane has focus, providing an ideal hook to update the hint bar's pane-specific row.

**Primary recommendation:** Replace `Footer()` with a custom `HintBar(Widget)` docked to the bottom. Use a single `reactive` string per row (pane hints and global hints), updated from `on_descendant_focus`. Keep all binding changes in `BINDINGS` class variables — do not put logic in `on_key`.

---

## 1. Custom Two-Row Footer

### Approach: Custom `HintBar` Widget (Claude's Discretion — recommended)

Do NOT subclass `Footer`. The built-in `Footer` reads `BINDINGS` from the focus chain and renders them automatically, but it renders only one row and its format is fixed (compact key chips). It cannot be made pane-aware without significant internal override.

**Recommended approach:** Replace `yield Footer()` in `JoyApp.compose()` with a custom widget:

```python
# src/joy/widgets/hint_bar.py
from textual.reactive import reactive
from textual.widget import Widget
from textual.app import RenderResult

class HintBar(Widget):
    """Two-row keyboard hint bar. Row 1: pane-specific. Row 2: global."""

    DEFAULT_CSS = """
    HintBar {
        dock: bottom;
        height: 2;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    """

    pane_hints: reactive[str] = reactive("")
    global_hints: reactive[str] = reactive(
        "O: Open defaults  s: Settings  r: Refresh  l: Legend  q: Quit  x: Sync"
    )

    def render(self) -> RenderResult:
        pane = self.pane_hints or ""
        glb = self.global_hints
        return f"{pane}\n{glb}"
```

`[VERIFIED: textual.textualize.io/guide/reactivity]` — Modifying a `reactive` attribute triggers automatic `render()` refresh with no extra plumbing.

**In `JoyApp`:**
```python
def compose(self) -> ComposeResult:
    yield Header()
    yield Grid(...)
    yield HintBar()  # replaces Footer()
```

**Update row 1 from `on_descendant_focus`** (hook already exists at app.py:420):

```python
PANE_HINTS = {
    "project-list":   "n: New project  e: Rename  D: Delete  R: Assign repo  /: Filter",
    "project-detail": "o: Open  e: Edit  n: Add  d: Delete  D: Force delete  space: Toggle default",
    "terminal-pane":  "e: Rename  Enter: Focus session",
    "worktrees-pane": "",   # empty per spec
}

def on_descendant_focus(self, event) -> None:
    # ... existing sub_title logic ...
    pane_id = _resolve_pane_id(event.widget)  # extract from existing logic
    hints = PANE_HINTS.get(pane_id, "")
    self.query_one(HintBar).pane_hints = hints
```

`[VERIFIED: codebase]` — `on_descendant_focus` already walks the DOM to find the focused pane ID; this is the exact same traversal logic.

### Alternative: `Static` widget with `.update()`

A `Static` widget updated via `.update(text)` also works. The difference from `HintBar(Widget)` is minor — `Static` defaults to single-line rendering; for two lines you'd use `\n` and set `height: 2`. Either approach is fine. `Widget` with `render()` is marginally cleaner since the content is always derived from the reactive, never manually assembled outside the widget.

`[ASSUMED]` — `Static` two-line rendering via `\n` in Textual 8.x works as expected; not explicitly verified in this session.

---

## 2. Key Binding Priority — Global vs Pane-Level

### How Textual resolves key conflicts

`[VERIFIED: textual.textualize.io/guide/input]` — When a key is pressed:

1. **Priority bindings are checked first** across the entire app/screen, regardless of focus.
2. **Focused widget BINDINGS** are searched next.
3. **DOM traversal upward** continues to `App`.

`priority=True` on a `Binding` means it always wins, even if a focused widget defines the same key. The current JoyApp uses `priority=True` on `n`, `s`, `r`, `l`, `O`.

### Key conflict risk for new globals b/m/i/y/u/t/h

None of these letters appear in any existing `BINDINGS` across the codebase:
- `ProjectList`: up/down/j/k/enter/e/D/delete//R
- `ProjectDetail`: escape/up/down/k/j/o/space/a/e/d
- `TerminalPane`: escape/up/down/k/j/enter
- `WorktreePane`: escape/up/down/k/j/enter
- `JoyApp`: q/O/n/s/r/l/x

`[VERIFIED: codebase grep]` — No conflict for b/m/i/y/u/t/h.

**`R` is already in `ProjectList.BINDINGS`** as `action_assign_repo`. The new global `R` (toggle auto-refresh) uses the same letter. Use `priority=True` on the global `R` OR rename: whichever pane has focus wins unless priority is set.

**Decision needed (Claude's Discretion):** The CONTEXT.md says `R` is unchanged in ProjectList (`R: Assign Repo`) AND the new global is `R: Auto-refresh`. These conflict. Options:
1. Move the auto-refresh toggle to a different key at the app level (e.g., keep `R` in ProjectList for assign-repo, and put toggle-refresh at the app level without `priority=True` so ProjectList's `R` wins when it has focus).
2. Give auto-refresh `priority=True` at app level, overriding ProjectList's `R`. ProjectList would need a different key for assign-repo.

**Recommendation:** Keep ProjectList's `R: Assign Repo` binding as-is. Add global `R: Auto-refresh` to JoyApp WITHOUT `priority=True`. When ProjectList has focus, `R` assigns repo. When any other pane has focus, `R` triggers auto-refresh. This matches the spec intent and avoids breaking existing ProjectList behavior.

`[ASSUMED]` — This non-priority resolution behavior is consistent with the documented focus-chain traversal. Needs testing.

### `n` key conflict

`JoyApp.BINDINGS` currently has `Binding("n", "new_project", "New", priority=True)`. The spec says `n` in ProjectDetail adds a new item. Because the app-level binding has `priority=True`, pressing `n` while ProjectDetail has focus will currently fire `action_new_project` in JoyApp, not `action_add_object` in ProjectDetail.

**Fix required:** Remove `priority=True` from `n` in JoyApp. With standard (non-priority) resolution, when ProjectDetail has focus, its own `n: Add` binding wins; when ProjectList or other panes have focus, the app-level `n: New project` wins.

`[VERIFIED: codebase]` — `Binding("n", "new_project", "New", priority=True)` is at app.py:54.

---

## 3. New Global Actions (b/m/i/y/u/t/h)

### Pattern from existing `action_open_all_defaults`

The pattern in `app.py:528-543` shows exactly how to find objects by type for the selected project:

```python
def action_open_all_defaults(self) -> None:
    detail = self.query_one(ProjectDetail)
    project = detail._project
    if project is None:
        return
    for _label, kinds in SEMANTIC_GROUPS:
        for kind in kinds:
            for item in project.objects:
                if item.kind == kind and item.open_by_default:
                    defaults.append(item)
```

The new globals follow the same pattern but filter by a single `PresetKind`:

```python
def _open_first_of_kind(self, kind: PresetKind) -> None:
    """Find the first object of given kind in the selected project and open/copy it."""
    detail = self.query_one(ProjectDetail)
    project = detail._project
    if project is None:
        self.notify("No project selected", markup=False)
        return
    item = next((obj for obj in project.objects if obj.kind == kind), None)
    if item is None:
        self.notify(f"No {kind.value} found for this project", markup=False)
        return
    self._do_open_global(item)

@work(thread=True, exit_on_error=False)
def _do_open_global(self, item: ObjectItem) -> None:
    from joy.operations import open_object
    try:
        open_object(item=item, config=self._config)
        self.notify(_success_message(item, self._config), markup=False)
    except Exception as exc:
        self.notify(f"Failed: {exc}", severity="error", markup=False)
```

**Kind mapping for global shortcuts:**
| Key | PresetKind | ObjectType | Operation |
|-----|-----------|------------|-----------|
| b | BRANCH | STRING | pbcopy to clipboard |
| m | MR | URL | open in browser |
| i | WORKTREE | WORKTREE | open in IDE |
| y | TICKET | URL | open in browser |
| u | NOTE | OBSIDIAN | open obsidian:// |
| t | THREAD | URL | open in browser |
| h | AGENTS | ITERM | activate iTerm2 session |

`[VERIFIED: codebase]` — `PRESET_MAP` in models.py confirms all these mappings.

### Notify on missing data

Use `self.notify(f"No {kind.value} found for this project", markup=False)` — this follows the existing pattern in `action_open_object` (project_detail.py:198) and `action_assign_repo` (project_list.py:337).

---

## 4. Binding Changes Impact

### Removing `a` from ProjectDetail

`[VERIFIED: codebase]` — Two tests reference pressing `"a"` to trigger the add-object flow:
- `tests/test_tui.py:411` — `test_a_adds_object` presses `"a"`, types a worktree path
- `tests/test_tui.py:449` — `test_a_escape_noop` presses `"a"` then escape

Both tests must be updated to press `"n"` instead. Test names should also be updated (e.g., `test_n_adds_object`, `test_n_escape_noop`).

No other test files reference `action_add_object` directly. `test_object_row.py` appears in the search results for the `add_object` query but it references `ObjectRow`, not the binding.

### Adding `D` (force delete) to ProjectDetail

`ProjectDetail` currently has `d` with confirmation modal (`action_delete_object`). The new `D` should call a new `action_force_delete_object` that skips the modal:

```python
def action_force_delete_object(self) -> None:
    """Delete highlighted object without confirmation (force delete)."""
    item = self.highlighted_object
    if item is None:
        self.app.notify("No object selected", severity="error", markup=False)
        return
    prev_cursor = self._cursor
    try:
        idx = self._project.objects.index(item)
        self._project.objects.pop(idx)
    except ValueError:
        return
    self._save_toggle()
    target_cursor = max(0, prev_cursor - 1)
    self._set_project_with_cursor(self._project, target_cursor)
    kind_val = item.kind.value
    value_display = _truncate(item.label if item.label else item.value)
    self.app.notify(f"Deleted: {kind_val} '{value_display}'", markup=False)
```

### Adding `e` (rename session) to TerminalPane

TerminalPane has no `e` binding currently. Add it — it opens a rename modal for the highlighted session. The rename uses AppleScript (`osascript`) similar to the existing `_do_activate` pattern.

### `n` in JoyApp — priority must be removed

See section 2 above. `n` currently has `priority=True` at the app level, which would swallow the ProjectDetail `n: Add` binding. Remove `priority=True` from the app-level `n` binding.

---

## 5. Complete Binding Inventory After Changes

### JoyApp.BINDINGS (after)
| Key | Action | Priority | Notes |
|-----|--------|----------|-------|
| q | quit | no | unchanged |
| O / shift+o | open_all_defaults | yes | unchanged |
| n | new_project | **no** | remove priority |
| s | settings | yes | unchanged |
| r | refresh_worktrees | yes | unchanged |
| l | legend | yes | unchanged |
| x | toggle_sync / disable_sync | no | unchanged |
| b | open_branch | no | new |
| m | open_mr | no | new |
| i | open_worktree_ide | no | new |
| y | open_ticket | no | new |
| u | open_note | no | new |
| t | open_thread | no | new |
| h | open_terminal | no | new |
| R | toggle_auto_refresh | no | new; no priority so ProjectList `R` wins when focused |

### ProjectDetail.BINDINGS (after)
| Key | Action | Notes |
|-----|--------|-------|
| escape | focus_list | unchanged |
| up/k | cursor_up | unchanged |
| down/j | cursor_down | unchanged |
| o | open_object | unchanged |
| space | toggle_default | unchanged |
| ~~a~~ | ~~add_object~~ | **REMOVED** |
| n | add_object | **NEW** (rename action or new binding) |
| e | edit_object | unchanged |
| d | delete_object | unchanged (with confirmation) |
| D | force_delete_object | **NEW** |

### ProjectList.BINDINGS (after)
Unchanged. Existing `R: Assign Repo`, `e: Rename`, `D: Delete` stay.

### TerminalPane.BINDINGS (after)
Add `e` for rename session. Everything else unchanged.

### WorktreePane.BINDINGS
Unchanged.

---

## 6. Common Pitfalls

### Pitfall 1: `priority=True` on app-level `n` swallows pane-level `n`
**What goes wrong:** ProjectDetail's `n: Add` never fires because app-level `priority=True` intercepts it first.
**Fix:** Remove `priority=True` from `Binding("n", "new_project", ...)` in JoyApp.
**Verified:** Current code has this issue — app.py:54.

### Pitfall 2: `R` key collision between global auto-refresh and ProjectList assign-repo
**What goes wrong:** If app-level `R: Auto-refresh` has `priority=True`, ProjectList's `R: Assign repo` never fires.
**Fix:** No `priority=True` on app-level `R`. With standard resolution, ProjectList's `R` wins when ProjectList is focused; app-level `R` fires from all other panes.

### Pitfall 3: `HintBar` not found when `on_descendant_focus` runs early
**What goes wrong:** `on_descendant_focus` fires before `HintBar` is mounted (during startup DOM construction), causing `NoMatches`.
**Fix:** Wrap `self.query_one(HintBar).pane_hints = hints` in a try/except or guard with `if self.is_attached`.

### Pitfall 4: Two-line height for HintBar
**What goes wrong:** Setting `height: 2` in CSS but content overflows or collapses.
**Fix:** `height: 2` with `render()` returning `f"{row1}\n{row2}"`. Each line is 1 terminal row. Confirmed standard pattern for fixed-height docked widgets.

### Pitfall 5: Tests using `"a"` key press
**What goes wrong:** After removing `a` binding, `test_a_adds_object` and `test_a_escape_noop` will silently fail (no binding → no action → assertion fails or passes for wrong reason).
**Fix:** Update both tests to press `"n"`. Rename test functions.

---

## Code Examples

### Global action using `_open_first_of_kind` helper
```python
# In JoyApp
def action_open_branch(self) -> None:
    """Copy branch to clipboard (global shortcut b)."""
    self._open_first_of_kind(PresetKind.BRANCH)

def action_open_mr(self) -> None:
    """Open MR in browser (global shortcut m)."""
    self._open_first_of_kind(PresetKind.MR)
```

### HintBar update in on_descendant_focus
```python
_PANE_HINTS: dict[str, str] = {
    "project-list":   "n: New  e: Rename  D: Delete  R: Assign repo  /: Filter",
    "project-detail": "o: Open  n: Add  e: Edit  d: Delete  D: Force delete  space: Toggle",
    "terminal-pane":  "e: Rename  Enter: Focus session",
    "worktrees-pane": "",
}

def on_descendant_focus(self, event) -> None:
    """Update sub_title and HintBar row 1 based on focused pane."""
    node = event.widget
    while node is not None:
        if hasattr(node, "id") and node.id in _PANE_HINTS:
            self.sub_title = {
                "project-detail": "Detail",
                "project-list": "Projects",
                "terminal-pane": "Terminal",
                "worktrees-pane": "Worktrees",
            }.get(node.id, "")
            try:
                self.query_one(HintBar).pane_hints = _PANE_HINTS[node.id]
            except Exception:
                pass
            return
        node = node.parent
```

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] — All existing bindings inventoried from source
- [VERIFIED: textual.textualize.io/guide/input] — Priority binding behavior, focus chain traversal
- [VERIFIED: textual.textualize.io/guide/reactivity] — reactive attribute auto-refresh behavior
- [VERIFIED: textual.textualize.io/widgets/footer/] — Footer widget internals; does not support multi-row

### Secondary (MEDIUM confidence)
- [ASSUMED] — `Static` two-line rendering via `\n` in Textual 8.x: standard pattern, not re-verified
- [ASSUMED] — Non-priority `R` resolution (ProjectList wins when focused): consistent with docs but needs test confirmation

---

## Metadata

**Confidence breakdown:**
- Binding inventory: HIGH — read from source
- HintBar approach: HIGH — reactive + render() is the documented pattern
- Priority conflict (n key): HIGH — verified in source
- R key resolution: MEDIUM — documented behavior, recommend smoke test
- Test impact: HIGH — exact line numbers verified

**Research date:** 2026-04-15
**Valid until:** 60 days (Textual 8.x stable API)
