---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/widgets/project_list.py
  - src/joy/widgets/project_detail.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Project rows in ProjectList show colored circle indicators for each Claude session linked to that project"
    - "Non-Claude terminals produce no indicators in ProjectList"
    - "Terminal rows in ProjectDetail show the claude state indicator next to session name for Claude sessions"
    - "Non-Claude terminal rows in ProjectDetail show no indicator"
  artifacts:
    - path: "src/joy/widgets/project_list.py"
      provides: "Claude state indicators rendered after project name"
    - path: "src/joy/widgets/project_detail.py"
      provides: "Claude state indicator prepended to terminal session labels"
  key_links:
    - from: "src/joy/widgets/project_list.py"
      to: "src/joy/resolver.py"
      via: "update_badges passes TerminalSession objects instead of just agent_count"
    - from: "src/joy/widgets/project_detail.py"
      to: "src/joy/models.py"
      via: "_build_virtual_rows reads session.is_claude and session.claude_state"
---

<objective>
Show Claude agent status indicators (busy/idle/waiting_input) in two locations:

1. **ProjectList**: After each project name, show colored circle indicators for all Claude sessions linked to that project. Green filled circle = busy, yellow filled circle = waiting_input, dim hollow circle = idle. Non-Claude terminals show nothing.

2. **ProjectDetail**: Next to each terminal session name in the Terminals group, show the claude state indicator if it is a Claude session. Non-Claude sessions show no indicator.

Purpose: Give the user instant visibility into which Claude agents are active, idle, or waiting for input across all projects, without needing to look at the terminal pane.

Output: Modified project_list.py and project_detail.py with indicator rendering.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/joy/widgets/project_list.py
@src/joy/widgets/project_detail.py
@src/joy/widgets/terminal_pane.py (indicator constants and rendering pattern)
@src/joy/widgets/object_row.py (ObjectRow rendering for detail pane)
@src/joy/resolver.py (RelationshipIndex.terminals_for returns list[TerminalSession])
@src/joy/models.py (TerminalSession has is_claude and claude_state fields)
@src/joy/app.py (update_badges and data flow)

<interfaces>
<!-- Key types and contracts the executor needs -->

From src/joy/models.py:
```python
@dataclass
class TerminalSession:
    session_id: str
    session_name: str
    foreground_process: str
    cwd: str
    tab_id: str = ""
    is_claude: bool = False
    claude_state: str | None = None  # "idle" | "busy" | "waiting_input" | None
```

From src/joy/resolver.py:
```python
class RelationshipIndex:
    def terminals_for(self, project: Project) -> list[TerminalSession]: ...
```

From src/joy/widgets/terminal_pane.py (reuse these constants):
```python
INDICATOR_BUSY = "\u25cf"           # filled circle -- green
INDICATOR_WAITING = "\u25cb"        # hollow circle -- dim
INDICATOR_WAITING_INPUT = "\u25cf"  # filled circle -- yellow
```

From src/joy/widgets/project_list.py:
```python
class ProjectRow(Static):
    @staticmethod
    def build_content(project, avail_width, mr_info, has, wt_count=0, agent_count=0, repo_name=None) -> Text: ...
    def set_counts(self, wt_count, agent_count, mr_info=None, avail_width=None) -> None: ...

class ProjectList(Widget):
    def update_badges(self, index, mr_data=None) -> None: ...
```

From src/joy/widgets/project_detail.py:
```python
class ProjectDetail(Widget):
    _resolver_terminals: list[TerminalSession]
    def _build_virtual_rows(self, project) -> dict[PresetKind, list[ObjectItem]]: ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Claude state indicators to ProjectList rows</name>
  <files>src/joy/widgets/project_list.py</files>
  <action>
Modify ProjectRow to display per-Claude-session indicators after the project name.

**Step 1: Change `build_content` signature and `set_counts` to accept session data.**

Replace `agent_count: int = 0` parameter in `build_content()` with `claude_states: list[str | None] = ()`. This list contains only Claude sessions' states (non-Claude terminals are excluded before passing). Each entry is "busy", "waiting_input", "idle", or None.

Replace `agent_count: int` parameter in `set_counts()` with `claude_states: list[str | None] = ()`. Also add `agent_count: int = 0` back as a separate param (still needed for the icon ribbon terminal presence check).

Update `__init__` to pass `claude_states=()` to `build_content()` and store it.

**Step 2: Render indicators in `build_content()` after the project name.**

After appending the project name text, if `claude_states` is non-empty, append a space then for each state in `claude_states`:
- `"busy"` -> append `"\u25cf"` (filled circle) with style `"green"`
- `"waiting_input"` -> append `"\u25cf"` (filled circle) with style `"yellow"`  
- `"idle"` or `None` -> append `"\u25cb"` (hollow circle) with style `"dim"`

The indicators should be rendered WITHOUT spaces between them (compact: "●●○"). Include this indicator string in the width budget: subtract its length from `name_budget` so alignment is preserved.

Specifically, compute `indicator_text` first (just the characters), then:
- `indicator_width = len(claude_states)` (each indicator is 1 char)
- Subtract `indicator_width + (1 if claude_states else 0)` from name_budget (the +1 is for the separating space)
- After appending the (possibly truncated) name and padding, append the space + indicators before the MR strip

**Step 3: Update `set_counts()` to store and pass claude_states.**

Store `self._claude_states = claude_states` and pass it through to `build_content()`.

**Step 4: Update `update_badges()` to extract claude_states from the RelationshipIndex.**

In `update_badges()`, change:
```python
agent_count = len(index.terminals_for(row.project))
```
to:
```python
terminals = index.terminals_for(row.project)
agent_count = len(terminals)
claude_states = [s.claude_state for s in terminals if s.is_claude]
```
Then pass both `agent_count` and `claude_states` to `row.set_counts()`.

The icon ribbon "terminal" icon still uses `agent_count > 0` to turn cyan (existing behavior preserved). The new `claude_states` list drives only the per-session indicators.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>
    - ProjectList rows show colored indicators (green/yellow/dim circles) after project name for each Claude session
    - Non-Claude terminals produce no indicators (only affect icon ribbon as before)
    - Row width accounting is correct: indicators are included in the layout budget so alignment is preserved
    - All existing tests pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Add Claude state indicators to ProjectDetail terminal rows</name>
  <files>src/joy/widgets/project_detail.py</files>
  <action>
Modify `_build_virtual_rows()` in ProjectDetail to enrich terminal session labels with a Claude state indicator.

**Step 1: Import indicator constants.**

At the top of project_detail.py, add:
```python
from joy.widgets.terminal_pane import INDICATOR_BUSY, INDICATOR_WAITING, INDICATOR_WAITING_INPUT, ICON_CLAUDE
```

**Step 2: Modify the TERMINALS virtual row synthesis in `_build_virtual_rows()`.**

In the loop `for session in self._resolver_terminals:`, when creating the `virt_item`, enrich the label for Claude sessions:

```python
for session in self._resolver_terminals:
    if session.is_claude:
        # Build label with state indicator
        if session.claude_state == "busy":
            indicator = f"{INDICATOR_BUSY} "  # green (styled by ObjectRow via label)
            prefix = f"{ICON_CLAUDE} "
        elif session.claude_state == "waiting_input":
            indicator = f"{INDICATOR_WAITING_INPUT} "  # yellow
            prefix = f"{ICON_CLAUDE} "
        else:
            indicator = f"{INDICATOR_WAITING} "  # idle/dim
            prefix = f"{ICON_CLAUDE} "
        label = f"{prefix}{session.session_name} {indicator.strip()}"
    else:
        label = session.session_name
    virt_item = ObjectItem(
        kind=PresetKind.TERMINALS,
        value=session.session_name,
        label=label,
        open_by_default=PresetKind.TERMINALS.value in default_kinds,
    )
    grouped.setdefault(PresetKind.TERMINALS, []).append(virt_item)
    self._readonly_items.add(id(virt_item))
```

Wait -- ObjectRow renders label as plain text via Static, which won't apply Rich styles to the indicator characters. The indicator characters themselves (filled/hollow circles) are visually distinct enough without color in this context, since the detail pane already uses the icon column for visual weight.

**Revised approach**: Keep it simpler. For Claude sessions, prepend the robot icon and append the state indicator character. The indicator character alone (filled vs hollow circle) conveys the state:
- busy: `"ICON_CLAUDE session_name INDICATOR_BUSY"` (filled circle = active)
- waiting_input: `"ICON_CLAUDE session_name INDICATOR_WAITING_INPUT"` (filled circle = needs attention)
- idle/None: `"ICON_CLAUDE session_name INDICATOR_WAITING"` (hollow circle = idle)

For non-Claude sessions: just use `session.session_name` as before (no change).

This matches the pattern used in terminal_pane.py's SessionRow._build_content() but adapted for plain-text labels in ObjectRow.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -m pytest tests/ -x -q --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>
    - Terminal rows in ProjectDetail show robot icon + state indicator for Claude sessions
    - Non-Claude terminal rows show just the session name (no change)
    - All existing tests pass
  </done>
</task>

</tasks>

<verification>
1. Run full test suite: `python -m pytest tests/ -x -q`
2. Visual check: Launch joy, observe ProjectList rows showing colored circles after project names for projects with Claude sessions
3. Visual check: Navigate to a project with Claude terminals in ProjectDetail, confirm robot icon and state indicator appear next to terminal session names
</verification>

<success_criteria>
- Claude session indicators visible in ProjectList next to project names (compact colored circles)
- Claude session indicators visible in ProjectDetail terminal rows (robot icon + state circle)
- Non-Claude terminals show no indicators in either location
- Row width alignment preserved in ProjectList (no layout breakage)
- All existing tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260429-ciy-show-claude-status-indicators-in-project/260429-ciy-SUMMARY.md`
</output>
