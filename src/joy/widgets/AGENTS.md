# Widgets

Textual `Widget` subclasses for the 3x2 grid panes. Each widget owns its layout, cursor, key bindings, and CSS.

## Pane Widgets

Grid is 3 columns x 2 rows (`grid-size: 3 2` in app.py CSS). Widgets mount in compose() order:

| Widget | File | Grid Cell | Purpose |
|--------|------|-----------|---------|
| `ProjectList` | `project_list.py` | Row 0, Col 0 | Project list with status ribbon, repo grouping, filter |
| `ProjectDetail` | `project_detail.py` | Row 0, Col 1 | Grouped objects (Code/Docs/Terminals) with virtual rows |
| `MRPane` | `mr_pane.py` | Row 0, Col 2 | Authored MRs + review requests |
| `TerminalPane` | `terminal_pane.py` | Row 1, Col 0 | iTerm2 sessions grouped by tab with Claude state |
| `WorktreePane` | `worktree_pane.py` | Row 1, Col 1 | Git worktrees grouped by repo with dirty/MR indicators |
| `PlaceholderPane` | `placeholder_pane.py` | Row 1, Col 2 | Empty spacer widget |

## Helper Widgets

| Widget | File | Purpose |
|--------|------|---------|
| `ObjectRow` | `object_row.py` | 3-column row: icon, value, kind. Used in ProjectDetail. |
| `HintBar` | `hint_bar.py` | 2-row footer: pane-specific hints + global quick-open keys |
| `GroupHeader` | (duplicated per pane) | Section separator. Duplicated to avoid cross-widget coupling. |

## Cursor Pattern

All focusable panes follow the same pattern:

```python
_cursor: int = -1  # -1 = no selection
_rows: list[SomeRowWidget] = []

def _update_highlight(self) -> None:
    for row in self._rows:
        row.remove_class("--highlight")
    if 0 <= self._cursor < len(self._rows):
        self._rows[self._cursor].add_class("--highlight")

def action_cursor_down(self) -> None:
    if self._cursor < len(self._rows) - 1:
        self._cursor += 1
        self._update_highlight()
```

- Integer index, not widget reference
- CSS class `.--highlight` toggled via `add_class()` / `remove_class()`
- Boundary clamping (no wraparound)
- `_update_highlight()` called after every cursor change
- Emits a `Message` subclass (e.g., `ProjectHighlighted`, `WorktreeHighlighted`) on cursor move

## CSS Conventions

Each widget has a `DEFAULT_CSS` class variable. All styling is self-contained.

```python
class WorktreePane(Widget, can_focus=True):
    DEFAULT_CSS = """
    WorktreePane {
        border: solid $surface-lighten-2;
    }
    WorktreePane:focus {
        border: solid $accent;
    }
    WorktreePane:focus-within {
        border: solid $accent;
    }
    """
```

**Rules:**
- Border: `solid $surface-lighten-2` (unfocused), `solid $accent` (focused)
- Both `:focus` and `:focus-within` pseudo-classes for border highlighting
- Row highlight: full accent when pane focused, 30% dimmed when not
- `.section-spacer` rules scoped to parent widget: `WorktreePane .section-spacer { ... }`
- `app.py` CSS contains only the `#pane-grid` layout rule. No widget styling in app.py.

## Data Flow

Widgets receive data through public `set_*()` methods, not constructor injection:

```python
# In app.py @work method:
self.query_one(WorktreePane).set_worktrees(worktrees)
self.query_one(TerminalPane).set_sessions(sessions, tab_groups)
self.query_one(ProjectList).set_projects(projects, repos)
```

Widgets never call adapters directly. All I/O flows through `app.py` background workers.

## Adding a New Pane

1. Create `src/joy/widgets/new_pane.py` inheriting `Widget, can_focus=True`
2. Add `DEFAULT_CSS` with border/focus rules (copy from `worktree_pane.py`)
3. Implement cursor pattern: `_cursor`, `_rows`, `_update_highlight()`, cursor actions
4. Define `Message` subclass for highlight events
5. Add `set_*()` method for data injection
6. Mount in `app.py` `compose()`, add to `_PANE_HINTS`, add message handler
7. Add widget pilot test in `tests/test_widget_new_pane.py`
