# Phase 21: UI Polish - Pattern Map

**Mapped:** 2026-05-08
**Files analyzed:** 6 modified files (5 widget files + app.py)
**Analogs found:** 6 / 6

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `src/joy/widgets/project_list.py` | component (widget) | event-driven | `src/joy/widgets/worktree_pane.py` | exact |
| `src/joy/widgets/project_detail.py` | component (widget) | event-driven | `src/joy/widgets/terminal_pane.py` | exact |
| `src/joy/widgets/worktree_pane.py` | component (widget) | event-driven | `src/joy/widgets/terminal_pane.py` | exact |
| `src/joy/widgets/terminal_pane.py` | component (widget) | event-driven | `src/joy/widgets/worktree_pane.py` | exact |
| `src/joy/widgets/mr_pane.py` | component (widget) | event-driven | `src/joy/widgets/worktree_pane.py` | exact |
| `src/joy/app.py` | config/layout | request-response | `src/joy/widgets/worktree_pane.py` | role-match (CSS migration source) |

---

## Pattern Assignments

### `src/joy/widgets/worktree_pane.py` (Issues 3)

**Change:** Add `WorktreePane:focus WorktreeRow.--highlight` rule — currently only `:focus-within` is present.

**Analog:** `src/joy/widgets/project_list.py` (ProjectList has both `:focus` and `:focus-within` as the reference implementation)

**Current DEFAULT_CSS (lines 247-278) — what exists:**
```python
DEFAULT_CSS = """
WorktreePane {
    height: 1fr;
    border: solid $surface-lighten-2;
}
WorktreePane:focus-within {
    border: solid $accent;
}
WorktreePane:focus {
    border: solid $accent;
}
WorktreePane .empty-state {
    width: 1fr;
    height: 1fr;
    content-align: center middle;
    color: $text-muted;
    text-style: dim;
}
WorktreePane:focus-within WorktreeRow.--highlight {
    background: $accent;
}
WorktreeRow.--highlight {
    background: $accent 30%;
}
WorktreeRow.--unlinked {
    color: $text-muted;
    text-style: dim;
}
WorktreePane .section-spacer {
    height: 1;
}
"""
```

**Reference pattern for the missing rule** (`project_list.py` lines 370-383):
```python
DEFAULT_CSS = """
ProjectList:focus-within ProjectRow.--highlight {
    background: $accent;
}
ProjectList:focus ProjectRow.--highlight {
    background: $accent;
}
ProjectRow.--highlight {
    background: $accent 30%;
}
ProjectList .section-spacer {
    height: 1;
}
"""
```

**Fix:** After `WorktreePane:focus-within WorktreeRow.--highlight { background: $accent; }`, add:
```css
WorktreePane:focus WorktreeRow.--highlight {
    background: $accent;
}
```

---

### `src/joy/widgets/terminal_pane.py` (Issue 4)

**Change:** Add `TerminalPane:focus SessionRow.--highlight` rule — same gap as WorktreePane.

**Analog:** `src/joy/widgets/worktree_pane.py` (both `:focus` and `:focus-within` pattern)

**Current DEFAULT_CSS (lines 193-220) — the missing rule slot:**
```python
DEFAULT_CSS = """
TerminalPane {
    height: 1fr;
    border: solid $surface-lighten-2;
}
TerminalPane:focus-within {
    border: solid $accent;
}
TerminalPane:focus {
    border: solid $accent;
}
TerminalPane:focus-within SessionRow.--highlight {
    background: $accent;
}
SessionRow.--highlight {
    background: $accent 30%;
}
TerminalPane .empty-state {
    width: 1fr;
    height: 1fr;
    content-align: center middle;
    color: $text-muted;
    text-style: dim;
}
TerminalPane .section-spacer {
    height: 1;
}
"""
```

**Fix:** After `TerminalPane:focus-within SessionRow.--highlight { background: $accent; }`, add:
```css
TerminalPane:focus SessionRow.--highlight {
    background: $accent;
}
```

---

### `src/joy/widgets/mr_pane.py` (Issues 5 and 7)

**Change 1 (Issue 5):** Add `MRPane:focus MRRow.--highlight` rule.
**Change 2 (Issue 7):** Scope `.section-spacer` to `MRPane .section-spacer`.

**Analog:** `src/joy/widgets/worktree_pane.py` for both the `:focus` highlight pattern and the scoped `.section-spacer` pattern.

**Current DEFAULT_CSS (lines 176-203) — showing both problems:**
```python
DEFAULT_CSS = """
MRPane {
    height: 1fr;
    border: solid $surface-lighten-2;
}
MRPane:focus-within {
    border: solid $accent;
}
MRPane:focus {
    border: solid $accent;
}
MRPane .empty-state {
    width: 1fr;
    height: 1fr;
    content-align: center middle;
    color: $text-muted;
    text-style: dim;
}
MRPane:focus-within MRRow.--highlight {
    background: $accent;
}
MRRow.--highlight {
    background: $accent 30%;
}
.section-spacer {              /* BUG: unscoped — matches any .section-spacer in DOM */
    height: 1;
}
"""
```

**Reference for scoped section-spacer** (`worktree_pane.py` line 275-277):
```css
WorktreePane .section-spacer {
    height: 1;
}
```

**Fix:**
```python
DEFAULT_CSS = """
...
MRPane:focus-within MRRow.--highlight {
    background: $accent;
}
MRPane:focus MRRow.--highlight {      # ADD this rule
    background: $accent;
}
MRRow.--highlight {
    background: $accent 30%;
}
MRPane .section-spacer {              # CHANGE: add MRPane scope
    height: 1;
}
"""
```

---

### `src/joy/widgets/project_detail.py` (Issues 2, 6, 9)

**Change 1 (Issue 2):** Add `ProjectDetail:focus ObjectRow.--highlight` rule.
**Change 2 (Issue 6):** Scope `.section-spacer` to `ProjectDetail .section-spacer`.
**Change 3 (Issue 9):** Add `border: solid $surface-lighten-2;` to ProjectDetail block + `:focus` and `:focus-within` border rules (currently absent — relies on app.py).

**Analog:** `src/joy/widgets/worktree_pane.py` — the complete self-contained border + focus + highlight + scoped-spacer pattern.

**Current DEFAULT_CSS (lines 68-87) — showing all three problems:**
```python
DEFAULT_CSS = """
ProjectDetail {
    width: 1fr;
    height: 1fr;
    overflow-y: auto;
    /* NO border rule — relies on app.py #project-detail { border: ... } */
}
ProjectDetail > VerticalScroll {
    width: 1fr;
    height: 1fr;
}
ProjectDetail:focus-within ObjectRow.--highlight {
    background: $accent;
    /* MISSING: ProjectDetail:focus ObjectRow.--highlight */
}
ObjectRow.--highlight {
    background: $accent 30%;
}
.section-spacer {              /* BUG: unscoped */
    height: 1;
}
"""
```

**Target state** (modelled on `worktree_pane.py` lines 247-278, adapted for ProjectDetail):
```python
DEFAULT_CSS = """
ProjectDetail {
    width: 1fr;
    height: 1fr;
    overflow-y: auto;
    border: solid $surface-lighten-2;   # ADD
}
ProjectDetail > VerticalScroll {
    width: 1fr;
    height: 1fr;
}
ProjectDetail:focus {                   # ADD
    border: solid $accent;
}
ProjectDetail:focus-within {            # ADD
    border: solid $accent;
}
ProjectDetail:focus-within ObjectRow.--highlight {
    background: $accent;
}
ProjectDetail:focus ObjectRow.--highlight {   # ADD
    background: $accent;
}
ObjectRow.--highlight {
    background: $accent 30%;
}
ProjectDetail .section-spacer {        # FIX: was unscoped `.section-spacer`
    height: 1;
}
"""
```

---

### `src/joy/widgets/project_list.py` (Issues 1 and 8)

**Change 1 (Issue 8):** Add `border: solid $surface-lighten-2;` to ProjectList block in DEFAULT_CSS.
**Change 2 (Issue 1, part A):** Add `:focus` and `:focus-within` border rules directly in DEFAULT_CSS.

**Analog:** `src/joy/widgets/worktree_pane.py` — self-contained border + focus pattern.

**Current DEFAULT_CSS (lines 370-383) — the gap:**
```python
DEFAULT_CSS = """
ProjectList:focus-within ProjectRow.--highlight {
    background: $accent;
}
ProjectList:focus ProjectRow.--highlight {
    background: $accent;
}
ProjectRow.--highlight {
    background: $accent 30%;
}
ProjectList .section-spacer {
    height: 1;
}
/* NO border rule — relies on app.py #project-list { border: ... } */
"""
```

**Reference pattern** (`worktree_pane.py` lines 247-257):
```python
DEFAULT_CSS = """
WorktreePane {
    height: 1fr;
    border: solid $surface-lighten-2;
}
WorktreePane:focus-within {
    border: solid $accent;
}
WorktreePane:focus {
    border: solid $accent;
}
...
"""
```

**Target state for ProjectList DEFAULT_CSS:**
```python
DEFAULT_CSS = """
ProjectList {
    height: 1fr;
    border: solid $surface-lighten-2;   # ADD
}
ProjectList:focus {                     # ADD
    border: solid $accent;
}
ProjectList:focus-within {             # ADD
    border: solid $accent;
}
ProjectList:focus-within ProjectRow.--highlight {
    background: $accent;
}
ProjectList:focus ProjectRow.--highlight {
    background: $accent;
}
ProjectRow.--highlight {
    background: $accent 30%;
}
ProjectList .section-spacer {
    height: 1;
}
"""
```

---

### `src/joy/app.py` (Issue 1, part B)

**Change:** After adding border + focus rules to ProjectList and ProjectDetail DEFAULT_CSS, remove the duplicate `#project-list` and `#project-detail` rules from JoyApp.CSS.

**Current JoyApp.CSS (lines 45-65) — what must be removed after migration:**
```python
CSS = """
#pane-grid {
    grid-size: 3 2;
    grid-rows: 1fr 1fr;
    grid-columns: 1fr 1fr 1fr;
}
#project-list {
    height: 1fr;
    border: solid $surface-lighten-2;     # REMOVE after ProjectList DEFAULT_CSS has it
}
#project-list:focus-within {
    border: solid $accent;                # REMOVE after ProjectList DEFAULT_CSS has it
}
#project-detail {
    height: 1fr;
    border: solid $surface-lighten-2;     # REMOVE after ProjectDetail DEFAULT_CSS has it
}
#project-detail:focus-within {
    border: solid $accent;                # REMOVE after ProjectDetail DEFAULT_CSS has it
}
"""
```

**After migration, JoyApp.CSS should only retain the grid layout rule:**
```python
CSS = """
#pane-grid {
    grid-size: 3 2;
    grid-rows: 1fr 1fr;
    grid-columns: 1fr 1fr 1fr;
}
"""
```

**CRITICAL ORDERING:** Add DEFAULT_CSS rules to widget files FIRST, then remove from app.py CSS in the same or a subsequent commit. Never remove app.py rules before widget rules exist — doing so leaves widgets with no border at all (RESEARCH.md Pitfall 4).

---

## Shared Patterns

### Self-Contained Border + Focus Pattern
**Source:** `src/joy/widgets/worktree_pane.py` lines 247-278 (gold standard — already correct)
**Apply to:** `project_list.py` and `project_detail.py`
```css
WidgetName {
    height: 1fr;
    border: solid $surface-lighten-2;
}
WidgetName:focus {
    border: solid $accent;
}
WidgetName:focus-within {
    border: solid $accent;
}
```

### Dual Focus Row Highlight Pattern
**Source:** `src/joy/widgets/project_list.py` lines 370-383 (has both `:focus` and `:focus-within`)
**Apply to:** `worktree_pane.py`, `terminal_pane.py`, `mr_pane.py`, `project_detail.py`
```css
WidgetName:focus-within RowWidget.--highlight {
    background: $accent;
}
WidgetName:focus RowWidget.--highlight {
    background: $accent;
}
RowWidget.--highlight {
    background: $accent 30%;
}
```

### Scoped Section Spacer Pattern
**Source:** `src/joy/widgets/worktree_pane.py` line 275, `src/joy/widgets/terminal_pane.py` line 217
**Apply to:** `mr_pane.py`, `project_detail.py`
```css
WidgetName .section-spacer {
    height: 1;
}
```

### Snapshot Baseline Update
**Source:** `tests/test_snapshots.py`
**Apply after:** All CSS fixes are complete
**Command:** `uv run pytest tests/test_snapshots.py --update-snapshot`
**Then verify:** `uv run pytest tests/test_snapshots.py -x -q`

---

## No Analog Found

None — all 9 issues are CSS-only fixes with direct analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `src/joy/widgets/`, `src/joy/app.py`, `tests/test_snapshots.py`
**Files read:** 8 (worktree_pane.py, terminal_pane.py, mr_pane.py, project_list.py, project_detail.py, placeholder_pane.py, hint_bar.py, app.py)
**Pattern extraction date:** 2026-05-08
