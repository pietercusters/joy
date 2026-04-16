---
phase: quick-260415-qqx
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/models.py
  - src/joy/store.py
  - src/joy/resolver.py
  - src/joy/widgets/object_row.py
  - src/joy/widgets/project_detail.py
  - src/joy/screens/confirmation.py
  - src/joy/terminal_sessions.py
  - src/joy/operations.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/app.py
  - tests/test_models.py
  - tests/test_store.py
  - tests/test_operations.py
  - tests/test_object_row.py
  - tests/test_propagation.py
  - tests/test_resolver.py
  - tests/test_sync.py
  - tests/conftest.py
  - tests/test_terminal_pane.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "All references to 'agents'/'AGENTS' in code are renamed to 'terminals'/'TERMINALS'"
    - "User can press n in TerminalPane to create a new named iTerm2 session"
    - "User can press e in TerminalPane to rename the highlighted session"
    - "User can press d in TerminalPane to close a session with confirmation"
    - "User can press D in TerminalPane to force-close a session with confirmation"
    - "Adding a Terminal object to a project auto-creates an iTerm2 session"
    - "Terminal objects are auto-removed from projects when their session disappears"
    - "Linked sessions show a project-link icon in the Terminals overview"
    - "Opening a Terminal object uses the Python API instead of AppleScript"
    - "Old TOML files with 'agents' kind are transparently read as 'terminals'"
    - "ConfirmationModal accepts a custom hint string"
    - "The stale field and --stale CSS are fully removed"
    - "All tests pass with the renamed enums and new functionality"
  artifacts:
    - path: "src/joy/models.py"
      provides: "PresetKind.TERMINALS enum, stale field removed from ObjectItem"
    - path: "src/joy/terminal_sessions.py"
      provides: "create_session(), rename_session(), close_session() functions"
    - path: "src/joy/operations.py"
      provides: "Python API based _open_iterm() replacing AppleScript"
    - path: "src/joy/widgets/terminal_pane.py"
      provides: "n/e/d/D bindings, linked_names flag display in SessionRow"
    - path: "src/joy/app.py"
      provides: "Auto-create hook, auto-remove logic, updated sync/propagation"
    - path: "src/joy/resolver.py"
      provides: "Renamed methods: terminals_for, project_for_terminal"
    - path: "src/joy/screens/confirmation.py"
      provides: "Parameterized hint text"
  key_links:
    - from: "src/joy/widgets/terminal_pane.py"
      to: "src/joy/terminal_sessions.py"
      via: "n/e/d/D actions call create/rename/close_session"
      pattern: "create_session|rename_session|close_session"
    - from: "src/joy/app.py"
      to: "src/joy/terminal_sessions.py"
      via: "_start_add_object_loop auto-create hook"
      pattern: "create_session"
    - from: "src/joy/app.py"
      to: "src/joy/resolver.py"
      via: "terminals_for/project_for_terminal calls"
      pattern: "terminals_for|project_for_terminal"
    - from: "src/joy/store.py"
      to: "src/joy/models.py"
      via: "backward compat alias agents->terminals in _toml_to_projects"
      pattern: "PresetKind.TERMINALS"
---

<objective>
Build full iTerm2 terminal session control in the joy TUI.

Purpose: Transform the read-only terminal session pane into a fully interactive terminal
management system. Users get n/e/d/D bindings to create, rename, and close iTerm2 sessions
directly from the TUI. Sessions auto-create when Terminal objects are added to projects and
auto-remove when they disappear. The entire "Agent" naming is replaced with "Terminal" throughout.

Output: All source and test files updated with Terminal naming, new iTerm2 Python API functions,
interactive TerminalPane bindings, auto-create/auto-remove logic, and linked session flag display.
</objective>

<execution_context>
@/Users/pieter/Github/joy/.claude/get-shit-done/workflows/execute-plan.md
@/Users/pieter/Github/joy/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260415-qqx-build-full-iterm2-terminal-session-contr/260415-qqx-CONTEXT.md
@.planning/quick/260415-qqx-build-full-iterm2-terminal-session-contr/260415-qqx-RESEARCH.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From src/joy/models.py:
```python
class PresetKind(str, Enum):
    AGENTS = "agents"  # RENAME TO: TERMINALS = "terminals"

class ObjectItem:
    kind: PresetKind
    value: str
    label: str = ""
    open_by_default: bool = False
    stale: bool = False  # REMOVE THIS FIELD

PRESET_MAP: dict[PresetKind, ObjectType]  # AGENTS key -> TERMINALS key

class Config:
    default_open_kinds: list[str]  # ["worktree", "agents"] -> ["worktree", "terminals"]
```

From src/joy/resolver.py:
```python
class RelationshipIndex:
    _ag_for_project: dict[str, list[TerminalSession]]
    _project_for_agent: dict[str, Project]
    def agents_for(self, project: Project) -> list[TerminalSession]
    def project_for_agent(self, session_name: str) -> Project | None

def compute_relationships(projects, worktrees, sessions, repos) -> RelationshipIndex
```

From src/joy/terminal_sessions.py:
```python
def fetch_sessions() -> list[TerminalSession] | None
def activate_session(session_id: str) -> bool
# ADD: create_session(name: str) -> str | None
# ADD: rename_session(session_id: str, new_name: str) -> bool
# ADD: close_session(session_id: str, force: bool = False) -> bool
```

From src/joy/screens/confirmation.py:
```python
class ConfirmationModal(ModalScreen[bool]):
    def __init__(self, title: str, prompt: str) -> None  # ADD: hint: str = "..."
```

From src/joy/widgets/terminal_pane.py:
```python
class TerminalPane(Widget, can_focus=True):
    async def set_sessions(self, sessions: list[TerminalSession] | None) -> None
    # CHANGE TO: set_sessions(self, sessions, *, linked_names: set[str] | None = None)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rename AGENTS to TERMINALS in models, store, resolver, and data layer</name>
  <files>
    src/joy/models.py
    src/joy/store.py
    src/joy/resolver.py
    src/joy/widgets/object_row.py
    src/joy/widgets/project_detail.py
  </files>
  <action>
**models.py:**
1. Rename `PresetKind.AGENTS = "agents"` to `PresetKind.TERMINALS = "terminals"`.
2. Update `PRESET_MAP` key from `PresetKind.AGENTS` to `PresetKind.TERMINALS`.
3. Remove the `stale: bool = False` field from `ObjectItem` dataclass entirely.
4. Remove any reference to `stale` from `ObjectItem` (the field, nothing in `to_dict` references it).
5. Update `Config.default_open_kinds` default from `["worktree", "agents"]` to `["worktree", "terminals"]`.

**store.py — _toml_to_projects():**
Add a backward-compatibility alias after the `kind = PresetKind(obj["kind"])` line. Before the
`PresetKind(...)` call, check if `obj["kind"] == "agents"` and silently replace it with `"terminals"`:
```python
raw_kind = obj["kind"]
if raw_kind == "agents":
    raw_kind = "terminals"  # backward compat: old TOML files
try:
    kind = PresetKind(raw_kind)
```
Also in `load_config()` for `default_open_kinds`: after reading the list, replace any `"agents"` entries
with `"terminals"` for backward compat.

**resolver.py:**
1. Rename `_ag_for_project` to `_term_for_project`.
2. Rename `_project_for_agent` to `_project_for_terminal`.
3. Rename method `agents_for()` to `terminals_for()`.
4. Rename method `project_for_agent()` to `project_for_terminal()`.
5. Rename local variable `agent_to_project` to `terminal_to_project` in `compute_relationships()`.
6. Update all `PresetKind.AGENTS` references to `PresetKind.TERMINALS`.

**object_row.py:**
1. Rename `KIND_SHORTCUT[PresetKind.AGENTS]` to `KIND_SHORTCUT[PresetKind.TERMINALS]`.
2. Rename `PRESET_ICONS[PresetKind.AGENTS]` to `PRESET_ICONS[PresetKind.TERMINALS]`.
3. Remove the `ObjectRow.--stale` CSS rules entirely (all four `.--stale` rules).

**project_detail.py:**
1. Rename `("Agents", [PresetKind.AGENTS])` to `("Terminals", [PresetKind.TERMINALS])` in `SEMANTIC_GROUPS`.
2. Remove the `if getattr(item, 'stale', False): row.add_class("--stale")` block from `_render_project()`.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -m pytest tests/test_models.py tests/test_store.py tests/test_resolver.py -x --no-header -q 2>&1 | tail -5</automated>
  </verify>
  <done>
    - PresetKind.TERMINALS exists, PresetKind.AGENTS does not
    - ObjectItem has no stale field
    - Config defaults to ["worktree", "terminals"]
    - store.py reads old "agents" TOML as PresetKind.TERMINALS
    - resolver uses terminals_for/project_for_terminal naming
    - object_row uses TERMINALS keys, no --stale CSS
    - SEMANTIC_GROUPS shows "Terminals"
  </done>
</task>

<task type="auto">
  <name>Task 2: Add create/rename/close to terminal_sessions.py and replace AppleScript opener</name>
  <files>
    src/joy/terminal_sessions.py
    src/joy/operations.py
  </files>
  <action>
**terminal_sessions.py — add three new functions following the existing `activate_session` pattern:**

1. `create_session(name: str) -> str | None` — Creates a new iTerm2 tab in the front window
   and sets its name. Returns session_id on success, None on failure. Uses lazy imports, 
   `Connection().run_until_complete()`, catch-all except. Implementation per RESEARCH.md:
   ```python
   def create_session(name: str) -> str | None:
       import iterm2
       from iterm2.connection import Connection
       result: str | None = None
       async def _create(connection):
           nonlocal result
           app = await iterm2.async_get_app(connection)
           window = app.current_window
           if window is None:
               return
           tab = await window.async_create_tab()
           if tab is None:
               return
           session = tab.sessions[0]
           await session.async_set_name(name)
           result = session.session_id
       try:
           Connection().run_until_complete(_create, retry=False)
       except Exception:
           pass
       return result
   ```

2. `rename_session(session_id: str, new_name: str) -> bool` — Renames a session. Returns True on
   success. Uses `app.get_session_by_id(session_id)` then `session.async_set_name(new_name)`.

3. `close_session(session_id: str, force: bool = False) -> bool` — Closes a session. `force=False`
   for graceful, `force=True` to skip iTerm2's confirmation. If session is None (already gone),
   return True. Uses `session.async_close(force=force)`.

**operations.py — replace `_open_iterm()`:**

Replace the AppleScript-based implementation with Python API. The new `_open_iterm` should:
1. Try to find an existing session by name by iterating all sessions (like fetch_sessions does).
2. If found, activate it (focus tab, bring window front).
3. If not found, create a new tab and set name.
4. Use lazy imports and Connection().run_until_complete() pattern.
5. Keep the same function signature `_open_iterm(item: ObjectItem, config: Config) -> None`.
6. Raise on failure (to match the opener contract — callers catch exceptions).

```python
@opener(ObjectType.ITERM)
def _open_iterm(item: ObjectItem, config: Config) -> None:
    """Create or focus a named iTerm2 session via Python API."""
    import iterm2
    from iterm2.connection import Connection

    name = item.value
    success = False

    async def _open(connection):
        nonlocal success
        app = await iterm2.async_get_app(connection)
        # Search for existing session by name
        for window in app.terminal_windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    if session.name == name:
                        await session.async_activate(select_tab=True, order_window_front=True)
                        await app.async_activate()
                        success = True
                        return
        # Not found: create new tab in front window
        window = app.current_window
        if window is None:
            return
        tab = await window.async_create_tab()
        if tab is None:
            return
        session = tab.sessions[0]
        await session.async_set_name(name)
        success = True

    Connection().run_until_complete(_open, retry=False)
    if not success:
        raise RuntimeError(f"Failed to open iTerm2 session '{name}'")
```

Remove the old `subprocess.run(["osascript", ...])` code and the `import subprocess` if no longer
needed at module level (check — _copy_string and _open_url still need it, so keep the import).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -c "from joy.terminal_sessions import create_session, rename_session, close_session; print('imports OK')" && python -c "from joy.operations import open_object; print('operations OK')"</automated>
  </verify>
  <done>
    - create_session, rename_session, close_session importable from terminal_sessions
    - _open_iterm uses Python API, no AppleScript
    - operations.py opener for ITERM type works with new implementation
  </done>
</task>

<task type="auto">
  <name>Task 3: Parameterize ConfirmationModal hint and add n/e/d/D bindings to TerminalPane</name>
  <files>
    src/joy/screens/confirmation.py
    src/joy/widgets/terminal_pane.py
  </files>
  <action>
**confirmation.py:**
Add `hint` parameter to `__init__` with default `"Enter to delete, Escape to cancel"`:
```python
def __init__(self, title: str, prompt: str, *, hint: str = "Enter to delete, Escape to cancel") -> None:
    super().__init__()
    self._title = title
    self._prompt = prompt
    self._hint = hint
```
In `compose()`, replace the hardcoded hint string with `self._hint`:
```python
yield Static(self._hint, classes="modal-hint")
```

**terminal_pane.py — add BINDINGS and action methods:**

1. Add to BINDINGS list:
```python
Binding("n", "new_session", "New", show=False),
Binding("e", "rename_session", "Rename", show=False),
Binding("d", "close_session", "Close", show=False),
Binding("D", "force_close_session", "Force Close", show=False),
```

2. Add `linked_names` parameter to `set_sessions()`:
```python
async def set_sessions(self, sessions: list[TerminalSession] | None, *, linked_names: set[str] | None = None) -> None:
```
Store `self._linked_names = linked_names or set()` at the top of the method.
Pass `is_linked=(session.session_name in self._linked_names)` to each `SessionRow` constructor.

3. Update `SessionRow.__init__` to accept `is_linked: bool = False` parameter. Store as `self.is_linked`.

4. Update `SessionRow._build_content()` to accept `is_linked: bool = False`. When `is_linked` is True,
   append a link icon at the end: `t.append("  \uf0c1", style="cyan")` (nf-fa-link icon U+F0C1).

5. Add `action_new_session()`:
```python
def action_new_session(self) -> None:
    """Create a new named terminal session (n key)."""
    from joy.screens import NameInputModal
    def on_name(name: str | None) -> None:
        if name is None:
            return
        self._do_create_session(name)
    self.app.push_screen(
        NameInputModal(title="New Terminal Session", placeholder="Session name"),
        on_name,
    )

@work(thread=True, exit_on_error=False)
def _do_create_session(self, name: str) -> None:
    import joy.terminal_sessions as _ts
    session_id = _ts.create_session(name)
    if session_id:
        self.app.call_from_thread(self.app.notify, f"Created session: {name}", markup=False)
        # Trigger refresh to pick up new session
        self.app.call_from_thread(self.app._load_terminal)
    else:
        self.app.call_from_thread(self.app.notify, "Failed to create session", severity="error", markup=False)
```

6. Add `action_rename_session()`:
```python
def action_rename_session(self) -> None:
    """Rename the highlighted session (e key)."""
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    row = self._rows[self._cursor]
    from joy.screens import NameInputModal
    def on_name(new_name: str | None) -> None:
        if new_name is None:
            return
        self._do_rename_session(row.session_id, new_name, row.session_name)
    self.app.push_screen(
        NameInputModal(title="Rename Session", initial_value=row.session_name, placeholder="Session name"),
        on_name,
    )

@work(thread=True, exit_on_error=False)
def _do_rename_session(self, session_id: str, new_name: str, old_name: str) -> None:
    import joy.terminal_sessions as _ts
    ok = _ts.rename_session(session_id, new_name)
    if ok:
        self.app.call_from_thread(self.app.notify, f"Renamed: {old_name} -> {new_name}", markup=False)
        # Per Conflict #5: update linked project obj.value if this session is linked
        self.app.call_from_thread(self._update_linked_project_name, old_name, new_name)
        # Trigger refresh to rebuild pane with new name
        self.app.call_from_thread(self.app._load_terminal)
    else:
        self.app.call_from_thread(self.app.notify, "Failed to rename session", severity="error", markup=False)

def _update_linked_project_name(self, old_name: str, new_name: str) -> None:
    """Update obj.value in linked project when session is renamed (Conflict #5)."""
    if not hasattr(self.app, '_rel_index') or self.app._rel_index is None:
        return
    project = self.app._rel_index.project_for_terminal(old_name)
    if project is None:
        return
    for obj in project.objects:
        if obj.kind == PresetKind.TERMINALS and obj.value == old_name:
            obj.value = new_name
            break
    # Persist and rebuild (Conflict #7)
    self.app._save_projects_bg()
```

7. Add `action_close_session()` (d key — graceful close with retry):
```python
def action_close_session(self) -> None:
    """Close the highlighted session with confirmation (d key)."""
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    row = self._rows[self._cursor]
    from joy.screens import ConfirmationModal
    def on_confirm(confirmed: bool) -> None:
        if not confirmed:
            return
        self._do_close_session(row.session_id, row.session_name, force=False)
    self.app.push_screen(
        ConfirmationModal("Close Session", f"Close '{row.session_name}'?", hint="Enter to close, Escape to cancel"),
        on_confirm,
    )

@work(thread=True, exit_on_error=False)
def _do_close_session(self, session_id: str, name: str, *, force: bool) -> None:
    import joy.terminal_sessions as _ts
    ok = _ts.close_session(session_id, force=force)
    if ok:
        self.app.call_from_thread(self.app.notify, f"Closed session: {name}", markup=False)
        self.app.call_from_thread(self.app._load_terminal)
    else:
        # Graceful close failed — offer force close
        if not force:
            self.app.call_from_thread(self._offer_force_close, session_id, name)
        else:
            self.app.call_from_thread(self.app.notify, f"Failed to close: {name}", severity="error", markup=False)

def _offer_force_close(self, session_id: str, name: str) -> None:
    """Push force-close confirmation after graceful close fails."""
    from joy.screens import ConfirmationModal
    def on_confirm(confirmed: bool) -> None:
        if not confirmed:
            return
        self._do_close_session(session_id, name, force=True)
    self.app.push_screen(
        ConfirmationModal("Force Close Session", f"Force close '{name}'? (running processes will be killed)",
                         hint="Enter to force close, Escape to cancel"),
        on_confirm,
    )
```

8. Add `action_force_close_session()` (D key — immediate force close with confirmation):
```python
def action_force_close_session(self) -> None:
    """Force-close the highlighted session with confirmation (D key)."""
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    row = self._rows[self._cursor]
    from joy.screens import ConfirmationModal
    def on_confirm(confirmed: bool) -> None:
        if not confirmed:
            return
        self._do_close_session(row.session_id, row.session_name, force=True)
    self.app.push_screen(
        ConfirmationModal("Force Close Session", f"Force close '{row.session_name}'?",
                         hint="Enter to force close, Escape to cancel"),
        on_confirm,
    )
```

Add `from joy.models import PresetKind` import at top of terminal_pane.py for the rename logic.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -c "from joy.screens.confirmation import ConfirmationModal; m = ConfirmationModal('T', 'P', hint='Custom'); print('hint OK')" && python -c "from joy.widgets.terminal_pane import TerminalPane; print([b.key for b in TerminalPane.BINDINGS])"</automated>
  </verify>
  <done>
    - ConfirmationModal accepts custom hint parameter
    - TerminalPane has n, e, d, D bindings
    - n opens NameInputModal and calls create_session
    - e opens NameInputModal with current name and calls rename_session
    - d opens ConfirmationModal, graceful close with force-close retry
    - D opens ConfirmationModal, immediate force close
    - SessionRow shows linked icon when is_linked=True
    - set_sessions accepts linked_names parameter
  </done>
</task>

<task type="auto">
  <name>Task 4: Update app.py — auto-create, auto-remove, sync rename, pane hints</name>
  <files>
    src/joy/app.py
  </files>
  <action>
**1. Rename all agent/AGENTS references throughout app.py:**
- `_propagate_agent_stale()` method: replace entirely with `_propagate_terminal_auto_remove()`
- All `agents_for()` calls -> `terminals_for()`
- All `project_for_agent()` calls -> `project_for_terminal()`
- `PresetKind.AGENTS` -> `PresetKind.TERMINALS`
- Update docstrings and comments accordingly
- In `action_open_terminal()`: `self._open_first_of_kind(PresetKind.TERMINALS)`

**2. Update `_PANE_HINTS`:**
Change `"terminal-pane"` value to `"o: Open  n: Add  e: Rename  d: Close  D: Force close"`.

**3. Replace `_propagate_agent_stale()` with `_propagate_terminal_auto_remove()`:**
```python
def _propagate_terminal_auto_remove(self) -> list[str]:
    """Auto-remove linked Terminal objects when their iTerm2 session disappears.

    Only runs when fetch_sessions() returned a non-empty list (timing guard).
    Mutates project.objects and returns notification messages.
    """
    messages: list[str] = []
    if not self._current_sessions:
        return messages  # empty/None = iTerm2 hiccup; skip removal
    active_sessions = {s.session_name for s in self._current_sessions}
    changed = False
    for project in self._projects:
        before_count = len(project.objects)
        removed_names = [
            obj.value for obj in project.objects
            if obj.kind == PresetKind.TERMINALS and obj.value not in active_sessions
        ]
        if removed_names:
            project.objects = [
                obj for obj in project.objects
                if not (obj.kind == PresetKind.TERMINALS and obj.value not in active_sessions)
            ]
            changed = True
            for name in removed_names:
                messages.append(f"\u2296 Removed terminal '{name}' from {project.name}")
    return messages
```

**4. Update `_propagate_changes()`:**
Replace `messages.extend(self._propagate_agent_stale())` with
`messages.extend(self._propagate_terminal_auto_remove())`.
Also update the save condition: auto-remove produces TOML mutations too, so save when
either MRs were added OR terminals were removed:
```python
mr_added = any("\u2295 Added PR" in m for m in messages)
terminal_removed = any("\u2296 Removed terminal" in m for m in messages)
if mr_added or terminal_removed:
    self._save_projects_bg()
```

**5. Update `_set_terminal_sessions()`:**
Pass `linked_names` to `set_sessions()`. After `_maybe_compute_relationships()`, if `_rel_index`
exists, compute the linked names set and pass it. However, since `_maybe_compute_relationships`
runs synchronously and builds `_rel_index`, we can pass linked names in the `set_sessions` call.

Actually, the cleaner approach: call `set_sessions` with sessions first, then after
`_maybe_compute_relationships()`, push linked_names to the pane separately. Add a small
method `TerminalPane.set_linked_names(linked_names: set[str])` that updates the stored set
and refreshes display. OR: pass it in the existing `set_sessions` call by computing it before.

The simplest approach matching the decision: compute `linked_names` from `_rel_index` after
it's available. Update `_maybe_compute_relationships()` to call `_update_terminal_link_status()`
after computing relationships:
```python
def _update_terminal_link_status(self) -> None:
    """Push linked session names to TerminalPane for flag display."""
    if self._rel_index is None:
        return
    linked_names: set[str] = set(self._rel_index._project_for_terminal.keys())
    try:
        self.query_one(TerminalPane).set_linked_names(linked_names)
    except Exception:
        pass
```
Add call `self._update_terminal_link_status()` at the end of `_maybe_compute_relationships()`.

In TerminalPane, add `set_linked_names(self, linked_names: set[str])` that stores the names
and re-renders the rows with updated link icons.

**6. Auto-create hook in `_start_add_object_loop()`:**
After `project.objects.append(obj)` and `self._save_projects_bg()`, add:
```python
if preset == PresetKind.TERMINALS:
    self._auto_create_terminal_session(value)
```
Add the worker method:
```python
@work(thread=True, exit_on_error=False)
def _auto_create_terminal_session(self, name: str) -> None:
    """Auto-create iTerm2 session when Terminal object added to project."""
    from joy.terminal_sessions import create_session
    session_id = create_session(name)
    if session_id:
        self.app.call_from_thread(self.app.notify, f"Created iTerm2 session: {name}", markup=False)
        self.app.call_from_thread(self.app._load_terminal)
    # Silently ignore failure — session can be created manually later
```
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -c "from joy.app import JoyApp, _PANE_HINTS; assert 'n: Add' in _PANE_HINTS['terminal-pane']; print('pane hints OK')" && python -c "from joy.app import JoyApp; assert hasattr(JoyApp, '_propagate_terminal_auto_remove'); print('auto-remove OK')"</automated>
  </verify>
  <done>
    - All agent/AGENTS references replaced with terminal/TERMINALS in app.py
    - _PANE_HINTS updated with n/e/d/D bindings
    - _propagate_agent_stale removed, replaced by _propagate_terminal_auto_remove
    - Auto-remove only runs when current_sessions is non-empty (timing guard)
    - Auto-remove mutates project.objects and saves TOML
    - _start_add_object_loop auto-creates iTerm2 session for TERMINALS preset
    - Terminal linked names pushed to TerminalPane after relationship computation
  </done>
</task>

<task type="auto">
  <name>Task 5: Add set_linked_names to TerminalPane for post-relationship flag display</name>
  <files>
    src/joy/widgets/terminal_pane.py
  </files>
  <action>
Add a `set_linked_names()` method to TerminalPane that allows app.py to push linked session names
after `_maybe_compute_relationships()` runs. This method updates the link icon on existing rows
without a full DOM rebuild:

```python
def set_linked_names(self, linked_names: set[str]) -> None:
    """Update linked status on existing rows. Called after relationship computation."""
    self._linked_names = linked_names
    for row in self._rows:
        if row.session_name in linked_names:
            if not row.is_linked:
                row.is_linked = True
                row.update(row._build_content(
                    TerminalSession(session_id=row.session_id, session_name=row.session_name,
                                    foreground_process="", cwd=""),
                    is_linked=True,
                ))
        else:
            if row.is_linked:
                row.is_linked = False
```

Actually, the simpler approach: store `_linked_names` on the pane. When `set_sessions` is called,
it uses `_linked_names` to set the flag. When `set_linked_names` is called after relationship
computation, it triggers a lightweight re-render of just the link icons.

Simplest reliable approach: `set_linked_names` stores the set and calls a refresh on each row.
Since rows are `Static` widgets, the cleanest way is to store `self._sessions_cache` (the raw
session list) in `set_sessions`, and when `set_linked_names` is called, re-call `set_sessions`
with the cached data + new linked_names.

Implementation:
1. Add `self._linked_names: set[str] = set()` and `self._sessions_cache: list[TerminalSession] | None = None` in `__init__`.
2. In `set_sessions()`, store `self._sessions_cache = sessions`.
3. Use `self._linked_names` when building SessionRow (pass `is_linked`).
4. `set_linked_names()` stores the set and re-calls `await self.set_sessions(self._sessions_cache)`.

```python
def set_linked_names(self, linked_names: set[str]) -> None:
    """Update linked session names and re-render rows with link icons."""
    self._linked_names = linked_names
    if self._sessions_cache is not None:
        # Re-render is fire-and-forget via call_after_refresh
        self.call_after_refresh(lambda: self.run_worker(self.set_sessions(self._sessions_cache)))
```

Wait — `set_sessions` is `async`. Use a simpler approach: since `set_linked_names` is called from
the main thread, just call `asyncio.ensure_future(self.set_sessions(self._sessions_cache))` or
use Textual's `self.run_worker`. Actually in Textual you can just do:

```python
async def set_linked_names(self, linked_names: set[str]) -> None:
    """Update linked session names and re-render rows with link icons."""
    self._linked_names = linked_names
    if self._sessions_cache is not None:
        await self.set_sessions(self._sessions_cache)
```

And in app.py `_update_terminal_link_status`, call it as an async method. Since app.py calls
are from the main thread, this works naturally.

Make the implementation clean and simple. Update `_update_terminal_link_status` in app.py to
be async-aware:
```python
async def _update_terminal_link_status(self) -> None:
    if self._rel_index is None:
        return
    linked_names: set[str] = set(self._rel_index._project_for_terminal.keys())
    try:
        await self.query_one(TerminalPane).set_linked_names(linked_names)
    except Exception:
        pass
```

And in `_maybe_compute_relationships`, since it's a sync method, use `self.call_after_refresh`:
```python
self.call_after_refresh(lambda: asyncio.ensure_future(self._update_terminal_link_status()))
```
Or simpler — make `_update_terminal_link_status` sync and have `set_linked_names` sync too, storing
the value and triggering a non-async re-render. The re-render just rebuilds the static content
of each row widget:

```python
def set_linked_names(self, linked_names: set[str]) -> None:
    """Update linked session names and refresh link icons on existing rows."""
    self._linked_names = linked_names
    for row in self._rows:
        is_linked = row.session_name in linked_names
        if row.is_linked != is_linked:
            row.is_linked = is_linked
            # Rebuild content — need original session data
            # Simplest: just store session on row
            row.update(row._build_content(row._session, is_claude=row._is_claude, is_busy=row._is_busy, is_linked=is_linked, show_shortcut=row._show_shortcut))
```

For this approach, store the original session + flags on each SessionRow during construction:
- `self._session = session`
- `self._is_claude = is_claude`
- `self._is_busy = is_busy`
- `self._show_shortcut = show_shortcut`
- `self.is_linked = is_linked`

Then `set_linked_names` can rebuild any row's content by calling `_build_content` with the stored data.

This is the cleanest approach. Implement it.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -c "from joy.widgets.terminal_pane import TerminalPane; assert hasattr(TerminalPane, 'set_linked_names'); print('set_linked_names OK')"</automated>
  </verify>
  <done>
    - TerminalPane.set_linked_names() stores linked names set
    - SessionRow stores original session data for re-rendering
    - Link icon appears on rows whose session_name is in linked_names
    - set_linked_names updates existing rows without full DOM rebuild
  </done>
</task>

<task type="auto">
  <name>Task 6: Update all tests for TERMINALS rename and new functionality</name>
  <files>
    tests/test_models.py
    tests/test_store.py
    tests/test_operations.py
    tests/test_object_row.py
    tests/test_propagation.py
    tests/test_resolver.py
    tests/test_sync.py
    tests/conftest.py
    tests/test_terminal_pane.py
  </files>
  <action>
**conftest.py:**
Replace `ObjectItem(kind=PresetKind.AGENTS, value="test-project-agents", label="Agents")` with
`ObjectItem(kind=PresetKind.TERMINALS, value="test-project-agents", label="Terminals")`.

**test_models.py:**
1. Replace `PresetKind.AGENTS.value == "agents"` assertion with `PresetKind.TERMINALS.value == "terminals"`.
2. Replace `PRESET_MAP[PresetKind.AGENTS]` with `PRESET_MAP[PresetKind.TERMINALS]`.
3. Update default_open_kinds assertions from `["worktree", "agents"]` to `["worktree", "terminals"]`.

**test_store.py:**
1. Update the default config TOML string assertion from `"agents"` to `"terminals"`.
2. Add a new test for backward compatibility: loading a TOML file with `kind = "agents"` should produce
   `PresetKind.TERMINALS` objects.
3. Add backward compat test for `default_open_kinds = ["worktree", "agents"]` being read as `["worktree", "terminals"]`.

**test_operations.py:**
1. Replace all `PresetKind.AGENTS` with `PresetKind.TERMINALS`.
2. Update the AppleScript test to test the new Python API behavior. Since the tests mock
   `subprocess.run`, they need to be rewritten to mock `iterm2` instead. The simplest approach:
   mock `joy.terminal_sessions.create_session` and `joy.terminal_sessions.activate_session` since
   `_open_iterm` now uses the Python API directly (not through terminal_sessions module, but inline).
   Actually, `_open_iterm` uses `iterm2` directly. So mock `iterm2.connection.Connection` and the
   async flow. Or simpler: since the old tests mocked `subprocess.run` for AppleScript, and the new
   code doesn't use subprocess, just verify the function is importable and the opener is registered.
   For the existing tests that check AppleScript escaping — those are no longer relevant. Replace them
   with simpler tests that verify the opener is registered for ObjectType.ITERM.

**test_object_row.py:**
Replace `PresetKind.AGENTS` with `PresetKind.TERMINALS`.

**test_propagation.py:**
This is the biggest change. The old tests test `_propagate_agent_stale()` which marks objects stale.
The new behavior is `_propagate_terminal_auto_remove()` which removes objects entirely.
1. Replace ALL `PresetKind.AGENTS` with `PresetKind.TERMINALS`.
2. Remove all `stale=True`/`stale=False` from ObjectItem constructors (field no longer exists).
3. Rewrite the stale-related test class to test auto-removal instead:
   - Test: Terminal object removed when session not in active sessions (non-empty list)
   - Test: Terminal object NOT removed when sessions list is empty (timing guard)
   - Test: Multiple projects, each loses their terminal objects
   - Test: No removal when session still active
4. Remove any tests for `obj.stale` field since it no longer exists.
5. Keep the `_propagate_mr_auto_add` tests unchanged (just update enum references).

**test_resolver.py:**
1. Replace `PresetKind.AGENTS` with `PresetKind.TERMINALS`.
2. Replace `agents_for()` calls with `terminals_for()`.
3. Replace `project_for_agent()` calls with `project_for_terminal()`.

**test_sync.py:**
1. Replace all `PresetKind.AGENTS` with `PresetKind.TERMINALS`.
2. Replace `agents_for()` with `terminals_for()`.
3. Replace `project_for_agent()` with `project_for_terminal()`.

**test_terminal_pane.py:**
Add tests for the new bindings if feasible with the existing test patterns. At minimum, verify
that the BINDINGS list contains the new keys (n, e, d, D).
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -m pytest tests/ -x --no-header -q --ignore=tests/test_tui.py --ignore=tests/test_pane_layout.py -k "not slow" 2>&1 | tail -10</automated>
  </verify>
  <done>
    - All test files use PresetKind.TERMINALS, never PresetKind.AGENTS
    - No test references ObjectItem.stale
    - Backward compat test: old "agents" TOML loads as TERMINALS
    - Propagation tests verify auto-removal (not stale marking)
    - Resolver tests use renamed methods
    - Sync tests use renamed methods
    - All tests pass
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| TUI -> iTerm2 API | Session names flow from user input to iTerm2 Python API |
| TOML -> models | User-editable TOML data loaded into model objects |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-qqx-01 | Injection | terminal_sessions.create_session | mitigate | Session names passed via Python API (async_set_name) not shell — no injection vector. Old AppleScript injection risk is eliminated by this change. |
| T-qqx-02 | Denial of Service | close_session(force=True) | accept | Force close kills session processes. Acceptable: user must confirm via ConfirmationModal. |
| T-qqx-03 | Information Disclosure | _propagate_terminal_auto_remove | accept | Notification shows session name when removed. Session names are not sensitive. |
| T-qqx-04 | Tampering | TOML backward compat | mitigate | Alias only maps known value "agents" to "terminals". Unknown values still rejected by PresetKind enum validation. |
</threat_model>

<verification>
1. `python -m pytest tests/ -x --no-header -q --ignore=tests/test_tui.py -k "not slow"` — all tests pass
2. `grep -r "PresetKind.AGENTS" src/` — returns zero matches
3. `grep -r "\.stale" src/joy/models.py` — returns zero matches
4. `grep -r "_propagate_agent_stale" src/` — returns zero matches
5. `python -c "from joy.models import PresetKind; PresetKind.TERMINALS"` — no error
6. `python -c "from joy.terminal_sessions import create_session, rename_session, close_session"` — imports OK
</verification>

<success_criteria>
- All "agent"/"AGENTS" naming replaced with "terminal"/"TERMINALS" across entire codebase
- Three new iTerm2 API functions (create/rename/close) in terminal_sessions.py
- AppleScript opener replaced with Python API in operations.py
- TerminalPane has functional n/e/d/D key bindings
- Auto-create: adding Terminal object to project creates iTerm2 session
- Auto-remove: vanished sessions remove Terminal objects (with non-empty guard)
- Linked sessions show project-link icon in TerminalPane
- ConfirmationModal accepts custom hint text
- Old TOML files with "agents" transparently load as "terminals"
- ObjectItem.stale field and all --stale CSS removed
- All tests pass with zero references to old naming
</success_criteria>

<output>
After completion, create `.planning/quick/260415-qqx-build-full-iterm2-terminal-session-contr/260415-qqx-SUMMARY.md`
</output>
