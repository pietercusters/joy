---
phase: quick-260414-nrt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/widgets/object_row.py
  - src/joy/widgets/project_detail.py
  - src/joy/widgets/worktree_pane.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/screens/legend.py
  - src/joy/screens/__init__.py
  - src/joy/app.py
  - tests/test_object_row.py
  - tests/test_legend.py
autonomous: true

must_haves:
  truths:
    - "Details pane renders 3-column rows: icon | value | kind (no dot, no label column)"
    - "Repo field appears at the top of the Details pane when project.repo is set"
    - "1 blank line appears before every section header in all panes (not before the first)"
    - "Pressing l opens a centered legend modal showing all icons from all panes"
    - "Legend modal dismisses on Escape or pressing l again"
    - "Kind column is right-aligned, value column wraps when content is long"
  artifacts:
    - path: "src/joy/widgets/object_row.py"
      provides: "3-column ObjectRow (Horizontal with icon/value/kind children)"
      contains: "class ObjectRow(Horizontal"
    - path: "src/joy/screens/legend.py"
      provides: "LegendModal with icon catalog"
      contains: "class LegendModal(ModalScreen"
    - path: "src/joy/screens/__init__.py"
      provides: "LegendModal export"
      contains: "LegendModal"
  key_links:
    - from: "src/joy/app.py"
      to: "src/joy/screens/legend.py"
      via: "l binding calls push_screen(LegendModal())"
      pattern: "action_legend"
    - from: "src/joy/widgets/object_row.py"
      to: "textual.containers.Horizontal"
      via: "ObjectRow base class"
      pattern: "class ObjectRow\\(Horizontal"
---

<objective>
Redesign the Details pane with a 3-column layout (icon | value | kind), add repo field to
the overview, add whitespace before section headers in all panes, and add a legend popup
modal on the `l` key.

Purpose: Improve readability of the Details pane by replacing the flat text rendering with
structured columns, and improve discoverability of icon meanings via a legend popup.

Output: Redesigned ObjectRow widget, repo field in Details, GroupHeader spacing in all 3
panes, and a new LegendModal screen.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260414-nrt-details-pane-redesign-columnar-layout-re/260414-nrt-CONTEXT.md
@.planning/quick/260414-nrt-details-pane-redesign-columnar-layout-re/260414-nrt-RESEARCH.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From src/joy/models.py:
```python
@dataclass
class ObjectItem:
    kind: PresetKind
    value: str
    label: str = ""
    open_by_default: bool = False
    object_type: ObjectType = ObjectType.STRING  # auto-derived

@dataclass
class Project:
    name: str
    objects: list[ObjectItem] = field(default_factory=list)
    created: date = field(default_factory=date.today)
    repo: str | None = None
```

From src/joy/widgets/object_row.py:
```python
PRESET_ICONS: dict[PresetKind, str] = {
    PresetKind.MR: "\ue725",
    PresetKind.BRANCH: "\ue0a0",
    PresetKind.TICKET: "\uf0ea",
    PresetKind.THREAD: "\uf086",
    PresetKind.FILE: "\uf15b",
    PresetKind.NOTE: "\uf040",
    PresetKind.WORKTREE: "\uf07b",
    PresetKind.AGENTS: "\uf120",
    PresetKind.URL: "\uf0ac",
}
```

From src/joy/screens/confirmation.py (modal pattern):
```python
class ConfirmationModal(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "Cancel"), ("enter", "confirm", "Confirm")]
    DEFAULT_CSS = """
    ConfirmationModal { align: center middle; }
    ConfirmationModal > Vertical { width: 60; height: auto; background: $surface; border: thick $background 80%; padding: 1 2; }
    """
    def action_cancel(self) -> None:
        self.dismiss(False)
```

From src/joy/app.py (existing BINDINGS):
```python
BINDINGS = [
    ("q", "quit", "Quit"),
    Binding("shift+o,O", "open_all_defaults", "Open All", priority=True),
    Binding("n", "new_project", "New", priority=True),
    Binding("s", "settings", "Settings", priority=True),
    Binding("r", "refresh_worktrees", "Refresh", priority=True),
]
```

Existing GroupHeader in project_detail.py, worktree_pane.py, terminal_pane.py:
```python
class GroupHeader(Static):
    DEFAULT_CSS = """
    GroupHeader { width: 1fr; height: 1; color: $text-muted; text-style: bold; padding: 0 1; }
    """
```

Worktree icon constants (src/joy/widgets/worktree_pane.py):
```python
ICON_BRANCH = "\ue0a0"
ICON_DIRTY = "\uf111"
ICON_NO_UPSTREAM = "\U000f0be1"
ICON_MR_OPEN    = "\uea64"
ICON_MR_DRAFT   = "\uebdb"
ICON_CI_PASS    = "\uf00c"
ICON_CI_FAIL    = "\uf00d"
ICON_CI_PENDING = "\uf192"
```

Terminal icon constants (src/joy/widgets/terminal_pane.py):
```python
ICON_SESSION = "\uf120"
ICON_CLAUDE = "\U000f1325"
INDICATOR_BUSY = "\u25cf"
INDICATOR_WAITING = "\u25cb"
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Redesign ObjectRow to 3-column Horizontal layout and add repo field to Details</name>
  <files>src/joy/widgets/object_row.py, src/joy/widgets/project_detail.py, tests/test_object_row.py</files>
  <behavior>
    - Test: ObjectRow.compose yields 3 Static children with classes col-icon, col-value, col-kind
    - Test: col-icon child contains the correct PRESET_ICON for the item's kind
    - Test: col-value child contains item.label (if set) or item.value
    - Test: col-kind child contains item.kind.value (e.g., "branch", "mr")
    - Test: No dot indicator (U+25CF/U+25CB) appears anywhere in the rendered children
    - Test: refresh_indicator() updates the col-value child (queries .col-value Static)
  </behavior>
  <action>
**ObjectRow redesign** (`src/joy/widgets/object_row.py`):

1. Change `ObjectRow` base class from `Static` to `Horizontal` (import `Horizontal` from `textual.containers`).
2. Keep `can_focus = False` on the class.
3. Replace `DEFAULT_CSS` with:
   ```
   ObjectRow {
       width: 1fr;
       height: auto;
       padding: 0 1;
   }
   ObjectRow .col-icon  { width: 3; }
   ObjectRow .col-value { width: 1fr; }
   ObjectRow .col-kind  { width: 12; text-align: right; color: $text-muted; }
   ```
   Note: `height: auto` allows value wrapping for long content.

4. Remove `_render_text()` static method entirely.
5. Add `compose()` method that yields 3 `Static` children:
   ```python
   def compose(self) -> ComposeResult:
       icon = PRESET_ICONS.get(self.item.kind, " ")
       value = self.item.label if self.item.label else self.item.value
       kind = self.item.kind.value
       yield Static(icon, classes="col-icon")
       yield Static(value, classes="col-value")
       yield Static(kind, classes="col-kind")
   ```
6. Update `__init__` — remove the `renderable = self._render_text(item)` call and `super().__init__(renderable, ...)`. Just call `super().__init__(**kwargs)` and store `self.item` and `self.index`.
7. Update `refresh_indicator()` to query the `.col-value` child:
   ```python
   def refresh_indicator(self) -> None:
       value = self.item.label if self.item.label else self.item.value
       self.query_one(".col-value", Static).update(value)
   ```
   The dot indicator is dropped per user decision — only icon/value/kind remain.

**Repo field in Details** (`src/joy/widgets/project_detail.py`):

8. In `_render_project()`, after `scroll.remove_children()` and before the `GROUP_ORDER` loop, add repo field rendering:
   ```python
   # Mount repo overview row (non-navigable) when project has a repo
   if self._project.repo:
       scroll.mount(Static(f"\uf401  {self._project.repo}", classes="repo-overview"))
   ```
   Add CSS for `.repo-overview` in `ProjectDetail.DEFAULT_CSS`:
   ```
   ProjectDetail .repo-overview {
       width: 1fr;
       height: 1;
       padding: 0 1;
       color: $text-muted;
   }
   ```
   The repo-overview row is NOT added to `_rows` — it is not cursor-navigable.

**Update tests** (`tests/test_object_row.py`):

9. Rewrite the existing tests. The old tests check for `_render_text()` returning a `rich.Text` with dot characters — that method no longer exists. Replace with tests that instantiate `ObjectRow` and check its `compose()` output. Since `compose()` yields plain widgets, test using:
   ```python
   row = ObjectRow(item, index=0)
   children = list(row.compose())
   # children[0] is icon Static, children[1] is value Static, children[2] is kind Static
   ```
   Keep the `_truncate` and `_success_message` tests unchanged (those helpers are not affected).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run pytest tests/test_object_row.py -x -v 2>&1 | tail -30</automated>
  </verify>
  <done>
    - ObjectRow renders 3 columns (icon | value | kind) via Horizontal with Static children
    - No dot indicator or label column in the output
    - Kind column shows item.kind.value, right-aligned via CSS
    - Value column fills remaining width, wraps on overflow (height: auto)
    - Repo field appears at the top of Details pane when project.repo is set
    - All tests in test_object_row.py pass with updated assertions
  </done>
</task>

<task type="auto">
  <name>Task 2: Add whitespace before GroupHeader in all panes</name>
  <files>src/joy/widgets/project_detail.py, src/joy/widgets/worktree_pane.py, src/joy/widgets/terminal_pane.py</files>
  <action>
Add a 1-line spacer `Static` before every `GroupHeader` except the first one rendered in each pane. This applies to all 3 panes that use `GroupHeader`.

**project_detail.py** — In `_render_project()`, track whether a group has already been rendered using a boolean `first_group = True`. Before each `GroupHeader` mount, if not the first group, mount a spacer:
```python
first_group = True
for kind in GROUP_ORDER:
    items = grouped.get(kind, [])
    if not items:
        continue
    if not first_group:
        scroll.mount(Static("", classes="section-spacer"))
    first_group = False
    scroll.mount(GroupHeader(GROUP_LABELS[kind]))
    ...
```
Add CSS to `ProjectDetail.DEFAULT_CSS`:
```
ProjectDetail .section-spacer {
    height: 1;
}
```

**worktree_pane.py** — In `set_worktrees()`, same pattern. Track `first_group = True` before the `for repo_name in sorted(...)` loop. Before each `GroupHeader` mount (the `await scroll.mount(GroupHeader(repo_name))` line), if not first group, mount spacer. Add CSS to `WorktreePane.DEFAULT_CSS`:
```
WorktreePane .section-spacer {
    height: 1;
}
```

**terminal_pane.py** — In `set_sessions()`, same pattern. There are two group sections (Claude and Other). Track `first_group = True` before the Claude group block. Mount spacer before the "Other" header if Claude group was already rendered. Add CSS to `TerminalPane.DEFAULT_CSS`:
```
TerminalPane .section-spacer {
    height: 1;
}
```

In all three files, use `Static("", classes="section-spacer")` as the spacer widget. Do NOT add spacer before the very first section — only between sections.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run pytest tests/ -x -v --ignore=tests/test_tui.py --ignore=tests/test_pane_layout.py --ignore=tests/test_refresh.py -k "not slow" 2>&1 | tail -20</automated>
  </verify>
  <done>
    - 1 blank line spacer appears before every GroupHeader except the first in project_detail.py
    - 1 blank line spacer appears before every GroupHeader except the first in worktree_pane.py
    - 1 blank line spacer appears before every GroupHeader except the first in terminal_pane.py
    - No existing tests broken by the spacer addition
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create LegendModal and wire l binding on JoyApp</name>
  <files>src/joy/screens/legend.py, src/joy/screens/__init__.py, src/joy/app.py, tests/test_legend.py</files>
  <behavior>
    - Test: LegendModal is a ModalScreen[None] subclass
    - Test: LegendModal.compose() yields content containing all Detail icons (PRESET_ICONS values)
    - Test: LegendModal.compose() yields content containing worktree icons (ICON_DIRTY, ICON_MR_OPEN, ICON_CI_PASS, ICON_CI_FAIL, ICON_CI_PENDING)
    - Test: LegendModal.compose() yields content containing terminal icons (ICON_CLAUDE, INDICATOR_BUSY, INDICATOR_WAITING)
    - Test: LegendModal has bindings for "escape" and "l" that both dismiss the modal
    - Test: LegendModal is exported from joy.screens
  </behavior>
  <action>
**Create LegendModal** (`src/joy/screens/legend.py`):

1. Create new file following the `ConfirmationModal` pattern:
   ```python
   """LegendModal: icon legend popup showing all icons used across all panes."""
   from __future__ import annotations

   from textual.app import ComposeResult
   from textual.containers import Vertical, VerticalScroll
   from textual.screen import ModalScreen
   from textual.widgets import Static
   ```

2. Define `LegendModal(ModalScreen[None])` with:
   - `BINDINGS = [("escape", "dismiss_legend", "Close"), ("l", "dismiss_legend", "Close")]`
   - `DEFAULT_CSS` following the ConfirmationModal style but wider (width: 70) for icon table readability. Use `$background 80%` border (non-destructive, unlike ConfirmationModal's `$error`).
   - Inner `VerticalScroll` for scrolling if the legend is longer than the visible modal area.

3. `compose()` method yields a `Vertical` containing:
   - A title `Static("Icon Legend", classes="modal-title")`
   - Section headers as bold `Static` widgets for "Details Pane", "Worktree Pane", "Terminal Pane"
   - Icon rows as `Static` widgets, each showing: `{icon}  {description}` using `rich.Text` with appropriate colors

   Organize the legend content as:

   **Details Pane:**
   - `\ue725` Merge Request
   - `\ue0a0` Branch
   - `\uf0ea` Ticket
   - `\uf086` Thread
   - `\uf15b` File
   - `\uf040` Note
   - `\uf07b` Worktree
   - `\uf120` Terminal / Agents
   - `\uf0ac` URL

   **Worktree Pane:**
   - `\ue0a0` Branch name (bold)
   - `\uf111` Uncommitted changes (yellow)
   - `\U000f0be1` No upstream remote (dim)
   - `\uea64` MR open (green)
   - `\uebdb` MR draft (dim)
   - `\uf00c` CI passed (green)
   - `\uf00d` CI failed (red)
   - `\uf192` CI pending (yellow)

   **Terminal Pane:**
   - `\uf120` Terminal session (bold)
   - `\U000f1325` Claude agent (bold)
   - `\u25cf` Claude busy (green)
   - `\u25cb` Claude waiting (dim)

   Use `rich.Text` to apply the correct color styles to icons (matching how they appear in the actual panes). For each icon row, build a `rich.Text`, append the icon with the correct style, then append the description text.

4. `action_dismiss_legend()` calls `self.dismiss(None)`.

5. `on_mount()` calls `self.focus()` (same as ConfirmationModal pattern).

**Update screens/__init__.py:**

6. Add `from joy.screens.legend import LegendModal` and add `"LegendModal"` to `__all__`.

**Wire l binding in JoyApp** (`src/joy/app.py`):

7. Add to `JoyApp.BINDINGS`:
   ```python
   Binding("l", "legend", "Legend", priority=True),
   ```

8. Add `action_legend()` method to `JoyApp`:
   ```python
   def action_legend(self) -> None:
       """Show icon legend popup."""
       from joy.screens import LegendModal  # noqa: PLC0415
       self.push_screen(LegendModal())
   ```
   Use lazy import matching the existing pattern in `action_settings()` and `action_delete_object()`.

**Create tests** (`tests/test_legend.py`):

9. Write unit tests verifying:
   - `LegendModal` is importable from `joy.screens`
   - `LegendModal` is a subclass of `ModalScreen`
   - `LegendModal` has `escape` and `l` in its BINDINGS
   - Calling `list(LegendModal().compose())` produces widgets (test that compose runs without error and yields content)
   - The composed content contains representative icons from each pane category (check by converting composed widgets to strings or inspecting their renderables for known icon codepoints)
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run pytest tests/test_legend.py tests/test_object_row.py -x -v 2>&1 | tail -30</automated>
  </verify>
  <done>
    - LegendModal exists at src/joy/screens/legend.py
    - LegendModal is exported from joy.screens
    - Pressing l anywhere opens a centered modal with icon legend organized by pane
    - Modal shows icons with correct colors matching their actual pane appearance
    - Modal dismisses on Escape or pressing l again
    - All legend tests pass
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new trust boundaries. All changes are UI-only (widget layout, modal display). No user
input processing, no external service calls, no data persistence changes.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-nrt-01 | I (Info Disclosure) | LegendModal | accept | Modal shows only hardcoded icon descriptions — no user data, no secrets. No risk. |
</threat_model>

<verification>
After all tasks complete:

1. Run full non-slow test suite:
   ```
   cd /Users/pieter/Github/joy && uv run pytest tests/ -x -v -k "not slow" 2>&1 | tail -40
   ```
2. Visual smoke test: `cd /Users/pieter/Github/joy && uv run joy`
   - Select a project with objects — verify 3-column layout (icon | value | kind)
   - Verify no dot indicators, no label column
   - Verify repo field at top of Details if project has repo set
   - Verify blank line before each section header (not before first)
   - Press `l` — verify legend modal appears centered
   - Press `l` again or Escape — verify modal dismisses
   - Navigate to WorktreePane and TerminalPane — verify spacers before headers there too
</verification>

<success_criteria>
- ObjectRow renders 3 columns (icon | value | kind) with no dot/label
- Repo field visible at top of Details pane when project.repo is set
- 1 blank line before every section header in all 3 panes (not before first)
- Legend modal opens on `l`, shows all icons organized by pane with correct colors
- Legend modal closes on Escape or `l`
- All tests pass (test_object_row.py, test_legend.py, full non-slow suite)
</success_criteria>

<output>
After completion, create `.planning/quick/260414-nrt-details-pane-redesign-columnar-layout-re/260414-nrt-SUMMARY.md`
</output>
