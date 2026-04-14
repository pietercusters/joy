---
phase: quick-260414-pob
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
  - src/joy/app.py
  - src/joy/models.py
  - tests/test_object_row.py
autonomous: true

must_haves:
  truths:
    - "ObjectRow shows an open indicator (filled circle) in the icon column when item.open_by_default is True"
    - "Pressing l when the legend is already open dismisses it (no stacking)"
    - "Details pane groups objects into three semantic groups: Code, Docs, Agents"
    - "Repo is rendered as a normal ObjectRow (not a special Static), cursor-navigable"
    - "All panes (project_detail, worktree_pane, terminal_pane) have consistent 2-space indent on items"
  artifacts:
    - path: "src/joy/widgets/object_row.py"
      provides: "ObjectRow with open_by_default indicator in icon column"
      contains: "open_by_default"
    - path: "src/joy/widgets/project_detail.py"
      provides: "Semantic group ordering (Code/Docs/Agents)"
      contains: "SEMANTIC_GROUPS"
    - path: "src/joy/models.py"
      provides: "PresetKind.REPO enum value"
      contains: "REPO"
  key_links:
    - from: "src/joy/app.py"
      to: "src/joy/screens/legend.py"
      via: "action_legend checks if LegendModal already showing"
      pattern: "is_screen_installed|screen_stack"
---

<objective>
Fix two bugs from the previous quick task (260414-nrt) and implement three improvements
to the Details pane and overall TUI consistency.

Purpose: Restore lost open_by_default indicator, fix legend l-key stacking, restructure
grouping semantics, normalize repo as a proper object, and apply consistent indentation.

Output: Updated ObjectRow, ProjectDetail, LegendModal, models, and pane CSS.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/260414-nrt-details-pane-redesign-columnar-layout-re/260414-nrt-PLAN.md

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
    AGENTS = "agents"
    URL = "url"

@dataclass
class ObjectItem:
    kind: PresetKind
    value: str
    label: str = ""
    open_by_default: bool = False

@dataclass
class Project:
    name: str
    objects: list[ObjectItem] = field(default_factory=list)
    created: date = field(default_factory=date.today)
    repo: str | None = None
```

From src/joy/widgets/object_row.py:
```python
class ObjectRow(Horizontal):
    def compose(self) -> ComposeResult:
        icon = PRESET_ICONS.get(self.item.kind, " ")
        value = self.item.label if self.item.label else self.item.value
        kind = self.item.kind.value
        yield Static(icon, classes="col-icon")
        yield Static(value, classes="col-value")
        yield Static(kind, classes="col-kind")
```

From src/joy/app.py (legend binding):
```python
Binding("l", "legend", "Legend", priority=True),

def action_legend(self) -> None:
    from joy.screens import LegendModal
    self.push_screen(LegendModal())
```

From src/joy/screens/legend.py:
```python
class LegendModal(ModalScreen[None]):
    BINDINGS = [
        ("escape", "dismiss_legend", "Close"),
        ("l", "dismiss_legend", "Close"),
    ]
```

From src/joy/widgets/project_detail.py:
```python
GROUP_ORDER: list[PresetKind] = [
    PresetKind.WORKTREE, PresetKind.BRANCH, PresetKind.MR,
    PresetKind.TICKET, PresetKind.THREAD, PresetKind.FILE,
    PresetKind.NOTE, PresetKind.AGENTS, PresetKind.URL,
]
```

WorktreeRow/SessionRow padding (indent pattern):
```python
# worktree_pane.py: WorktreeRow CSS has `padding: 0 1;`
# terminal_pane.py: SessionRow CSS has `padding: 0 1;`
# object_row.py: ObjectRow CSS has `padding: 0 1;`
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Bug fixes — restore open indicator and fix legend l-key stacking</name>
  <files>src/joy/widgets/object_row.py, src/joy/app.py, src/joy/screens/legend.py, tests/test_object_row.py</files>
  <behavior>
    - Test: ObjectRow.compose() yields a col-icon Static containing U+25CF (filled circle) when item.open_by_default is True
    - Test: ObjectRow.compose() yields a col-icon Static that does NOT contain U+25CF when item.open_by_default is False
    - Test: refresh_indicator() updates the col-icon child when open_by_default changes
    - Test: LegendModal BINDINGS contain "l" mapped to dismiss action (already tested in test_legend.py — confirm not broken)
  </behavior>
  <action>
**Bug 1: Restore open indicator in ObjectRow** (`src/joy/widgets/object_row.py`):

The 260414-nrt redesign removed the dot indicator (U+25CF/U+25CB) entirely. Restore it by
prepending the filled circle indicator to the icon column when `item.open_by_default` is True.

1. In `compose()`, build the icon text to include the open indicator before the kind icon:
   ```python
   def compose(self) -> ComposeResult:
       indicator = "\u25cf " if self.item.open_by_default else "  "
       icon = PRESET_ICONS.get(self.item.kind, " ")
       value = self.item.label if self.item.label else self.item.value
       kind = self.item.kind.value
       yield Static(f"{indicator}{icon}", classes="col-icon")
       yield Static(value, classes="col-value")
       yield Static(kind, classes="col-kind")
   ```

2. Widen the `col-icon` CSS from `width: 3` to `width: 5` to accommodate the 2-char indicator prefix plus the icon character plus spacing.

3. Update `refresh_indicator()` to also refresh the icon column (since toggling open_by_default changes the indicator):
   ```python
   def refresh_indicator(self) -> None:
       indicator = "\u25cf " if self.item.open_by_default else "  "
       icon = PRESET_ICONS.get(self.item.kind, " ")
       self.query_one(".col-icon", Static).update(f"{indicator}{icon}")
       value = self.item.label if self.item.label else self.item.value
       self.query_one(".col-value", Static).update(value)
   ```

**Bug 2: Fix legend l-key stacking** (`src/joy/app.py`):

The problem: `action_legend` in JoyApp has `priority=True` on the `l` binding. When the
LegendModal is open, the app-level binding fires BEFORE the modal's own `l` binding because
`priority=True` bindings on the App are checked before screen-level bindings. This causes a
new LegendModal to be pushed on top.

Fix by making `action_legend()` check whether a LegendModal is already on the screen stack:
```python
def action_legend(self) -> None:
    """Toggle icon legend popup — dismiss if already open, else show."""
    from joy.screens import LegendModal  # noqa: PLC0415
    # Check if a LegendModal is already on the screen stack
    for screen in self.screen_stack:
        if isinstance(screen, LegendModal):
            screen.dismiss(None)
            return
    self.push_screen(LegendModal())
```

The LegendModal `l` binding in legend.py is fine and does not need changes. The fix is
purely in `action_legend` which now acts as a toggle.

**Update tests** (`tests/test_object_row.py`):

4. Update `test_no_dot_indicator_in_compose` — rename to `test_open_indicator_shown_when_open_by_default`:
   ```python
   def test_open_indicator_shown_when_open_by_default():
       item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=True)
       row = ObjectRow(item, index=0)
       children = list(row.compose())
       icon_text = _get_content(children[0])
       assert "\u25cf" in icon_text
   ```

5. Add `test_no_open_indicator_when_not_default`:
   ```python
   def test_no_open_indicator_when_not_default():
       item = ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=False)
       row = ObjectRow(item, index=0)
       children = list(row.compose())
       icon_text = _get_content(children[0])
       assert "\u25cf" not in icon_text
   ```

6. Update `test_refresh_indicator_updates_col_value` to also verify col-icon is updated.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run pytest tests/test_object_row.py tests/test_legend.py -x -v 2>&1 | tail -30</automated>
  </verify>
  <done>
    - ObjectRow shows filled circle (U+25CF) before the kind icon when open_by_default is True
    - ObjectRow shows no indicator when open_by_default is False
    - refresh_indicator() updates both icon and value columns
    - Pressing l when legend is open dismisses it instead of stacking a new one
    - All tests in test_object_row.py and test_legend.py pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Semantic grouping, repo as object, and consistent indent</name>
  <files>src/joy/models.py, src/joy/widgets/project_detail.py, src/joy/widgets/object_row.py, src/joy/widgets/worktree_pane.py, src/joy/widgets/terminal_pane.py, src/joy/screens/legend.py</files>
  <action>
**Change 3: Rethink grouping to semantic groups** (`src/joy/widgets/project_detail.py`):

Replace the flat `GROUP_ORDER` list with a semantic grouping structure. Replace `GROUP_ORDER`
and `GROUP_LABELS` with:

```python
# Semantic group structure for Details pane
SEMANTIC_GROUPS: list[tuple[str, list[PresetKind]]] = [
    ("Code", [PresetKind.REPO, PresetKind.WORKTREE, PresetKind.MR, PresetKind.BRANCH]),
    ("Docs", [PresetKind.TICKET, PresetKind.NOTE, PresetKind.URL, PresetKind.FILE, PresetKind.THREAD]),
    ("Agents", [PresetKind.AGENTS]),
]
```

Update `_render_project()` to iterate over `SEMANTIC_GROUPS` instead of `GROUP_ORDER`:

```python
first_group = True
for group_label, kinds in SEMANTIC_GROUPS:
    group_items: list[ObjectItem] = []
    for kind in kinds:
        group_items.extend(grouped.get(kind, []))
    if not group_items:
        continue
    if not first_group:
        scroll.mount(Static("", classes="section-spacer"))
    first_group = False
    scroll.mount(GroupHeader(group_label))
    for item in group_items:
        row = ObjectRow(item, index=row_index)
        scroll.mount(row)
        new_rows.append(row)
        row_index += 1
```

Remove the old `GROUP_ORDER` and `GROUP_LABELS` constants. Update the import in `app.py`
line 16: change `from joy.widgets.project_detail import GROUP_ORDER, ProjectDetail` to
`from joy.widgets.project_detail import SEMANTIC_GROUPS, ProjectDetail`. Then update
`action_open_all_defaults()` in app.py — it currently iterates `GROUP_ORDER` to collect
default items. Update it to iterate `SEMANTIC_GROUPS`:

```python
defaults: list[ObjectItem] = []
for _label, kinds in SEMANTIC_GROUPS:
    for kind in kinds:
        for item in project.objects:
            if item.kind == kind and item.open_by_default:
                defaults.append(item)
```

**Change 4: Repo as a proper Project object** (`src/joy/models.py`, `src/joy/widgets/project_detail.py`, `src/joy/widgets/object_row.py`):

4a. Add `PresetKind.REPO = "repo"` to the `PresetKind` enum in `models.py`. Add it to
`PRESET_MAP` mapping to `ObjectType.URL` (repo URLs are opened in the browser).

4b. Add a repo icon to `PRESET_ICONS` in `object_row.py`:
```python
PresetKind.REPO: "\uf401",   # nf-oct-repo (same icon used in the old repo-overview Static)
```

4c. In `project_detail.py` `_render_project()`, remove the special-cased repo-overview
Static block entirely (the `if self._project.repo:` block that mounts `.repo-overview`).
Remove the `.repo-overview` CSS rule from `ProjectDetail.DEFAULT_CSS`.

Instead, synthesize a temporary `ObjectItem` for the repo and inject it into the grouped
dict so it renders through the normal ObjectRow path:

```python
# Synthesize repo ObjectItem if project has a repo URL
if self._project.repo:
    repo_item = ObjectItem(kind=PresetKind.REPO, value=self._project.repo, label="")
    grouped.setdefault(PresetKind.REPO, []).append(repo_item)
```

This must happen BEFORE the `SEMANTIC_GROUPS` iteration. The repo item will appear in the
"Code" group (first position since REPO is first in the Code kinds list), and is
cursor-navigable (it gets added to `_rows` through the normal loop). Opening it with `o`
will use the URL object_type to open in the browser.

4d. Add the repo icon and description to the LegendModal Details section (`legend.py`).
Insert as the first entry in the Details Pane list:
```python
("\uf401", "Repository", ""),
```

**Change 5: Consistent indent in all panes** — All three row types already use `padding: 0 1`
which provides 1 character of left padding. The worktree_pane WorktreeRow has its content
indented with a leading space in `build_content()` (the ` {ICON_BRANCH} ` string starts with
a space). For consistency:

5a. In `object_row.py`, update the `col-icon` CSS to add 1 extra left padding:
```
ObjectRow .col-icon  { width: 5; padding: 0 0 0 1; }
```
This gives ObjectRow items a visual indent of ~2 spaces from the group header.

5b. In `terminal_pane.py` `SessionRow`, the content already starts with the icon character
directly. Add 1 leading space before the icon in `_build_content()` — change both the
claude and non-claude paths:
```python
# Claude path:
t.append(f" {ICON_CLAUDE} ", style="bold")
# Non-claude path:
t.append(f" {ICON_SESSION} ", style="bold")
```
Wait — looking at the code, terminal_pane SessionRow line 126 already has `f"{ICON_CLAUDE} "`
without a leading space, while worktree_pane WorktreeRow line 171 has `f" {ICON_BRANCH} "`
WITH a leading space. Add the leading space to SessionRow to match:
```python
# Line 126: change f"{ICON_CLAUDE} " to f" {ICON_CLAUDE} "
# Line 134: change f"{ICON_SESSION} " to f" {ICON_SESSION} "
```

5c. For project_detail ObjectRow, the left padding on `.col-icon` via CSS achieves the same
visual effect as the leading space in worktree/terminal content strings. No additional changes
needed beyond the CSS padding already specified in 5a.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && uv run pytest tests/ -x -v -k "not slow" --ignore=tests/test_tui.py --ignore=tests/test_pane_layout.py --ignore=tests/test_refresh.py 2>&1 | tail -30</automated>
  </verify>
  <done>
    - Details pane shows three semantic groups: Code, Docs, Agents (in that order)
    - Repo appears as a normal cursor-navigable ObjectRow in the Code group (not a special Static)
    - PresetKind.REPO exists in models.py with PRESET_MAP and PRESET_ICONS entries
    - Opening repo with 'o' opens the repo URL in the browser
    - LegendModal includes repo icon entry
    - All panes have consistent ~2 space visual indent for items under group headers
    - All non-slow tests pass
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new trust boundaries. All changes are UI-only (widget layout, modal dismiss logic,
enum additions). No user input processing, no external service calls, no data persistence
changes. The repo URL is already stored in Project.repo and opened via existing open_object
machinery.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-pob-01 | I (Info Disclosure) | LegendModal toggle | accept | Modal shows only hardcoded icon descriptions. Toggle logic is cosmetic. No risk. |
| T-pob-02 | T (Tampering) | Synthesized repo ObjectItem | accept | Repo ObjectItem is created in-memory from Project.repo (already trusted data). Not persisted. No risk. |
</threat_model>

<verification>
After all tasks complete:

1. Run full non-slow test suite:
   ```
   cd /Users/pieter/Github/joy && uv run pytest tests/ -x -v -k "not slow" --ignore=tests/test_tui.py --ignore=tests/test_pane_layout.py --ignore=tests/test_refresh.py 2>&1 | tail -40
   ```
2. Visual smoke test: `cd /Users/pieter/Github/joy && uv run joy`
   - Select a project with objects and a repo set
   - Verify filled circle indicator shows on open_by_default items in icon column
   - Verify no indicator on non-default items
   - Toggle an item with Space — verify indicator updates
   - Verify groups are labeled Code, Docs, Agents (not kind names)
   - Verify repo appears as first item in Code group, cursor-navigable, openable with 'o'
   - Press `l` — verify legend opens
   - Press `l` again — verify legend DISMISSES (no stacking)
   - Verify consistent indent across all panes
</verification>

<success_criteria>
- Open indicator (filled circle) visible in ObjectRow icon column for open_by_default items
- Pressing l toggles legend (open/close), never stacks
- Details groups: Code (repo, worktrees, mrs, branches), Docs (tickets, notes, urls, files, threads), Agents
- Repo rendered as ObjectRow, cursor-navigable, openable
- Consistent ~2 space indent on items in all panes
- All non-slow tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260414-pob-details-pane-fixes-and-improvements-open/260414-pob-SUMMARY.md`
</output>
