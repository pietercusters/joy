# Architecture Research: joy

**Project:** joy -- keyboard-driven Python TUI for managing coding project artifacts
**Researched:** 2026-04-10
**Overall confidence:** HIGH

---

## Component Overview

joy has five major components. Each has a single responsibility and communicates through well-defined interfaces.

| Component | Responsibility | Depends On |
|-----------|---------------|------------|
| **Data Model** (`models.py`) | Dataclasses for Project, ObjectItem, Config. Pure data, no I/O. | Nothing |
| **Store** (`store.py`) | Read/write `~/.joy/` TOML files. Serialize/deserialize models. | Data Model |
| **Operations** (`operations.py`) | Type-dispatched actions: open URL, copy to clipboard, launch IDE, etc. | Data Model, subprocess |
| **Widgets** (`widgets/`) | Custom Textual widgets: ProjectList, ProjectDetail, ObjectRow. | Data Model |
| **App + Screens** (`app.py`, `screens/`) | Textual App, MainScreen, SettingsScreen, modals. Wires everything together. | All above |

**Data flows in one direction:** Store loads data into Models, Models feed Widgets, user actions on Widgets trigger Operations, Operations may update Models, Store persists changes.

```
Store --reads/writes--> Models <--renders-- Widgets
                           ^                    |
                           |                    v
                       Operations <--triggers-- User Input
```

---

## Data Model

Use plain Python dataclasses. Pydantic adds startup time and is overkill for this data shape. Dataclasses give type hints, `__eq__`, `__repr__`, and `asdict()` for free.

### Core Types

```python
# models.py
from dataclasses import dataclass, field
from enum import Enum
from datetime import date


class ObjectType(str, Enum):
    """All supported object types. The str mixin makes TOML serialization trivial."""
    STRING = "string"
    URL = "url"
    OBSIDIAN = "obsidian"
    FILE = "file"
    WORKTREE = "worktree"
    ITERM = "iterm"


class PresetKind(str, Enum):
    """Pre-defined object kinds that map to an ObjectType + default behavior."""
    MR = "mr"              # ObjectType.URL, browser
    BRANCH = "branch"      # ObjectType.STRING, clipboard
    TICKET = "ticket"      # ObjectType.URL, Notion desktop
    THREAD = "thread"      # ObjectType.URL, Slack desktop
    FILE = "file"          # ObjectType.FILE, editor
    NOTE = "note"          # ObjectType.OBSIDIAN, Obsidian
    WORKTREE = "worktree"  # ObjectType.WORKTREE, IDE
    AGENTS = "agents"      # ObjectType.ITERM, iTerm2
    URL = "url"            # ObjectType.URL, browser


# Maps preset kinds to their underlying type
PRESET_TYPE_MAP: dict[PresetKind, ObjectType] = {
    PresetKind.MR: ObjectType.URL,
    PresetKind.BRANCH: ObjectType.STRING,
    PresetKind.TICKET: ObjectType.URL,
    PresetKind.THREAD: ObjectType.URL,
    PresetKind.FILE: ObjectType.FILE,
    PresetKind.NOTE: ObjectType.OBSIDIAN,
    PresetKind.WORKTREE: ObjectType.WORKTREE,
    PresetKind.AGENTS: ObjectType.ITERM,
    PresetKind.URL: ObjectType.URL,
}


@dataclass
class ObjectItem:
    """A single artifact within a project."""
    kind: PresetKind          # e.g., "mr", "branch", "ticket"
    value: str                # The actual data: URL, path, branch name, etc.
    label: str = ""           # Optional display label (defaults to value if empty)
    open_by_default: bool = False

    @property
    def object_type(self) -> ObjectType:
        return PRESET_TYPE_MAP[self.kind]

    @property
    def display_label(self) -> str:
        return self.label or self.value


@dataclass
class Project:
    """A project with its list of artifacts."""
    name: str
    objects: list[ObjectItem] = field(default_factory=list)
    created: date = field(default_factory=date.today)

    @property
    def default_objects(self) -> list[ObjectItem]:
        """Objects marked for open-by-default."""
        return [obj for obj in self.objects if obj.open_by_default]


@dataclass
class Config:
    """Global configuration."""
    ide: str = "PyCharm"           # Application name for `open -a`
    editor: str = "Sublime Text"   # Application name for `open -a`
    obsidian_vault: str = ""       # Vault name (not path) for obsidian:// URIs
    terminal: str = "iTerm2"       # Terminal app (future-proofing)
    default_open_kinds: list[str] = field(
        default_factory=lambda: ["worktree", "agents"]
    )
```

### Why This Design

**Two-level type system (PresetKind + ObjectType):** PresetKind is what users see and interact with ("mr", "ticket", "branch"). ObjectType is what the operations layer dispatches on (URL, STRING, FILE). This separation means:
- Adding a new preset kind (e.g., "design" for Figma URLs) only requires adding an enum value and a mapping entry -- no new operation code.
- The operations layer stays small: 6 handlers for 6 ObjectTypes, not 9+ for every preset kind.
- Users don't need to know about ObjectType; they pick from the preset list.

**Dataclasses not Pydantic:** joy's data is simple and trusted (we write it ourselves). Pydantic's validation overhead and import time are unnecessary. If validation becomes needed later, adding `__post_init__` to dataclasses is straightforward.

---

## ~/.joy/ Directory Layout

```
~/.joy/
  config.toml        # Global settings
  projects.toml      # All project data in one file
```

### config.toml

```toml
# Global settings for joy

ide = "PyCharm"
editor = "Sublime Text"
obsidian_vault = "wiki"
terminal = "iTerm2"

# Object kinds to mark as open_by_default when creating a new project
default_open_kinds = ["worktree", "agents"]
```

### projects.toml

```toml
[[project]]
name = "joy"
created = 2026-04-10

[[project.object]]
kind = "worktree"
value = "/Users/pieter/Github/joy"
label = ""
open_by_default = true

[[project.object]]
kind = "mr"
value = "https://gitlab.com/user/joy/-/merge_requests/1"
label = "Main MR"
open_by_default = true

[[project.object]]
kind = "branch"
value = "feature/tui-layout"
label = ""
open_by_default = true

[[project.object]]
kind = "note"
value = "Projects/joy"
label = "Project notes"
open_by_default = false

[[project]]
name = "other-project"
created = 2026-03-15

[[project.object]]
kind = "ticket"
value = "https://notion.so/ticket-123"
label = "PROJ-123"
open_by_default = true
```

### Rationale: Single File, Not Directory-Per-Project

- **Data volume is tiny.** Dozens of projects, each with ~5-15 objects. A single `projects.toml` will be <10KB even with 50 projects.
- **Atomic operations.** Writing one file is simpler and safer than coordinating across multiple files. No partial-state issues.
- **Easy backup.** Copy two files, done.
- **TOML's `[[array_of_tables]]` syntax** handles the project-list-with-nested-objects shape cleanly.
- **When to reconsider:** If projects.toml grows past 100KB or users want per-project version control. Neither is likely for a personal tool.

### Store Implementation Pattern

```python
# store.py
import tomllib
import tomli_w
from pathlib import Path
from models import Project, ObjectItem, Config

JOY_DIR = Path.home() / ".joy"
CONFIG_PATH = JOY_DIR / "config.toml"
PROJECTS_PATH = JOY_DIR / "projects.toml"


def ensure_joy_dir() -> None:
    """Create ~/.joy/ if it doesn't exist."""
    JOY_DIR.mkdir(exist_ok=True)


def load_config() -> Config:
    """Load global config, returning defaults if file missing."""
    if not CONFIG_PATH.exists():
        return Config()
    with open(CONFIG_PATH, "rb") as f:
        data = tomllib.load(f)
    return Config(**data)


def save_config(config: Config) -> None:
    """Write global config to TOML."""
    ensure_joy_dir()
    from dataclasses import asdict
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(asdict(config), f)


def load_projects() -> list[Project]:
    """Load all projects from TOML."""
    if not PROJECTS_PATH.exists():
        return []
    with open(PROJECTS_PATH, "rb") as f:
        data = tomllib.load(f)
    projects = []
    for p in data.get("project", []):
        objects = [
            ObjectItem(**obj) for obj in p.get("object", [])
        ]
        projects.append(Project(
            name=p["name"],
            objects=objects,
            created=p.get("created", date.today()),
        ))
    return projects


def save_projects(projects: list[Project]) -> None:
    """Write all projects to TOML."""
    ensure_joy_dir()
    from dataclasses import asdict
    data = {"project": []}
    for p in projects:
        pd = {"name": p.name, "created": p.created}
        pd["object"] = [asdict(obj) for obj in p.objects]
        data["project"].append(pd)
    with open(PROJECTS_PATH, "wb") as f:
        tomli_w.dump(data, f)
```

**Key decisions:**
- Functions, not a class. There is no state to manage -- read file, return data. Write data, done.
- Load returns full list, save writes full list. The data is small enough that incremental updates add complexity without benefit.
- `ensure_joy_dir()` creates `~/.joy/` on first write so users don't need to run a setup command.

---

## Textual App Structure

### File Layout

```
src/joy/
    __init__.py
    app.py              # JoyApp class, main() entry point
    models.py           # Dataclasses: Project, ObjectItem, Config
    store.py            # TOML read/write functions
    operations.py       # Type-dispatched open/copy/launch actions
    screens/
        __init__.py
        main.py         # MainScreen (two-pane layout)
        settings.py     # SettingsScreen (global config editor)
    widgets/
        __init__.py
        project_list.py # Left pane: project list with keyboard nav
        project_detail.py # Right pane: object list for selected project
        object_row.py   # Single object row with icon + label + status
    styles/
        app.tcss        # Global styles
        main.tcss       # MainScreen styles
        settings.tcss   # SettingsScreen styles
```

### Widget Hierarchy

```
JoyApp
  +-- MainScreen
  |     +-- Header (optional, or custom TitleBar)
  |     +-- Horizontal
  |     |     +-- ProjectList (left pane, docked)
  |     |     |     +-- ListView
  |     |     |           +-- ListItem (per project)
  |     |     +-- ProjectDetail (right pane)
  |     |           +-- VerticalScroll
  |     |                 +-- ObjectRow (per object)
  |     +-- Footer
  |
  +-- SettingsScreen (pushed on top when activated)
  |     +-- Config form widgets
  |
  +-- ConfirmModal (pushed for delete confirmations)
  +-- ObjectFormModal (pushed for add/edit object)
  +-- ProjectFormModal (pushed for new project)
```

### App Class

```python
# app.py
from textual.app import App
from screens.main import MainScreen


class JoyApp(App):
    """Keyboard-driven project artifact manager."""

    TITLE = "joy"
    CSS_PATH = "styles/app.tcss"

    # App-level bindings (available everywhere)
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("?", "help", "Help"),
    ]

    SCREENS = {
        "main": MainScreen,
    }

    def on_mount(self) -> None:
        self.push_screen("main")


def main() -> None:
    app = JoyApp()
    app.run()
```

### MainScreen: The Two-Pane Layout

```python
# screens/main.py
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer
from widgets.project_list import ProjectList
from widgets.project_detail import ProjectDetail


class MainScreen(Screen):
    CSS_PATH = "main.tcss"  # Relative to app CSS_PATH

    # Screen-level bindings
    BINDINGS = [
        ("a", "add_object", "Add"),
        ("e", "edit_object", "Edit"),
        ("d", "delete_object", "Delete"),
        ("o", "open_object", "Open"),
        ("O", "open_defaults", "Open All"),
        ("space", "toggle_default", "Toggle Default"),
        ("n", "new_project", "New Project"),
        ("s", "settings", "Settings"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ProjectList(id="project-list")
            yield ProjectDetail(id="project-detail")
        yield Footer()
```

### CSS for Two-Pane Layout

```css
/* styles/main.tcss */
#project-list {
    dock: left;
    width: 30;
    height: 100%;
    border-right: solid $primary-background;
}

#project-detail {
    width: 1fr;
    height: 100%;
    overflow-y: auto;
}
```

**Why dock instead of grid:** Docking the project list to the left is simpler, keeps it fixed during scrolling, and matches the mental model of a sidebar. Grid layout would work but adds unnecessary complexity for a two-column split.

### Custom Widget: ProjectList

```python
# widgets/project_list.py
from textual.widgets import ListView, ListItem, Label
from textual.widget import Widget
from textual.app import ComposeResult
from textual.message import Message
from models import Project


class ProjectList(Widget, can_focus=True):
    """Left pane: list of projects."""

    class ProjectHighlighted(Message):
        """Sent when user moves highlight to a project."""
        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()

    class ProjectSelected(Message):
        """Sent when user presses enter on a project."""
        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._projects: list[Project] = []

    def compose(self) -> ComposeResult:
        yield ListView(id="project-listview")

    def set_projects(self, projects: list[Project]) -> None:
        """Populate the list with projects."""
        self._projects = projects
        listview = self.query_one("#project-listview", ListView)
        listview.clear()
        for project in projects:
            listview.append(ListItem(Label(project.name)))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Bubble a ProjectHighlighted message when highlight changes."""
        if event.index is not None and event.index < len(self._projects):
            self.post_message(self.ProjectHighlighted(self._projects[event.index]))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Bubble a ProjectSelected message when enter is pressed."""
        if event.index is not None and event.index < len(self._projects):
            self.post_message(self.ProjectSelected(self._projects[event.index]))
```

### Custom Widget: ProjectDetail

```python
# widgets/project_detail.py
from textual.widget import Widget
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from models import Project
from widgets.object_row import ObjectRow


class ProjectDetail(Widget, can_focus=True):
    """Right pane: shows objects for the selected project."""

    project: reactive[Project | None] = reactive(None, recompose=True)

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
    ]

    def compose(self) -> ComposeResult:
        if self.project is None:
            yield VerticalScroll(id="detail-empty")
        else:
            with VerticalScroll(id="detail-scroll"):
                for i, obj in enumerate(self.project.objects):
                    yield ObjectRow(obj, index=i)
```

---

## Object Type System

### Pattern: functools.singledispatch

Use `singledispatch` from the standard library. It is the Pythonic way to dispatch behavior based on type, avoids giant if/elif chains, and is extensible without modifying existing code.

However, since we dispatch on an enum value (not a Python type), we use a simple dictionary registry instead -- this is cleaner than singledispatch for string/enum dispatch.

```python
# operations.py
import subprocess
import webbrowser
from typing import Callable
from models import ObjectItem, ObjectType, Config

# Type alias for an opener function
Opener = Callable[[ObjectItem, Config], None]

# Registry: ObjectType -> opener function
_OPENERS: dict[ObjectType, Opener] = {}


def opener(obj_type: ObjectType):
    """Decorator to register an opener for an ObjectType."""
    def decorator(fn: Opener) -> Opener:
        _OPENERS[obj_type] = fn
        return fn
    return decorator


def open_object(item: ObjectItem, config: Config) -> None:
    """Open an object using its type-specific handler."""
    handler = _OPENERS.get(item.object_type)
    if handler is None:
        raise ValueError(f"No opener registered for {item.object_type}")
    handler(item, config)


# --- Registered openers ---

@opener(ObjectType.URL)
def _open_url(item: ObjectItem, config: Config) -> None:
    """Open a URL in the default browser or registered app."""
    subprocess.run(["open", item.value], check=True)


@opener(ObjectType.STRING)
def _copy_string(item: ObjectItem, config: Config) -> None:
    """Copy a string to the clipboard."""
    subprocess.run(
        ["pbcopy"], input=item.value.encode("utf-8"), check=True
    )


@opener(ObjectType.FILE)
def _open_file(item: ObjectItem, config: Config) -> None:
    """Open a file in the configured editor."""
    subprocess.run(["open", "-a", config.editor, item.value], check=True)


@opener(ObjectType.WORKTREE)
def _open_worktree(item: ObjectItem, config: Config) -> None:
    """Open a git worktree directory in the configured IDE."""
    subprocess.run(["open", "-a", config.ide, item.value], check=True)


@opener(ObjectType.OBSIDIAN)
def _open_obsidian(item: ObjectItem, config: Config) -> None:
    """Open a file in Obsidian via URI scheme."""
    from urllib.parse import quote
    vault = config.obsidian_vault
    file_path = quote(item.value)
    uri = f"obsidian://open?vault={vault}&file={file_path}"
    subprocess.run(["open", uri], check=True)


@opener(ObjectType.ITERM)
def _open_iterm(item: ObjectItem, config: Config) -> None:
    """Create or activate a named iTerm2 window."""
    name = item.value
    script = f'''
    tell application "iTerm2"
        activate
        set targetWindow to missing value
        repeat with w in windows
            if name of w is "{name}" then
                set targetWindow to w
                exit repeat
            end if
        end repeat
        if targetWindow is missing value then
            set targetWindow to (create window with default profile)
            tell current session of targetWindow
                set name to "{name}"
            end tell
        end if
        select targetWindow
    end tell
    '''
    subprocess.run(["osascript", "-e", script], check=True)
```

### Why This Pattern

- **Simple dict registry vs. class hierarchy:** Each ObjectType needs a single function (open/activate). A full class hierarchy (AbstractOpener -> URLOpener -> etc.) is over-engineered for functions that are 3-5 lines each.
- **Decorator registration:** The `@opener(ObjectType.URL)` pattern keeps the registration co-located with the implementation. No separate registration step needed.
- **Extensible:** Adding a new ObjectType means: (1) add enum value, (2) write a 3-line function with `@opener` decorator. No other code changes.
- **Testable:** Each opener function is independently testable. The registry can be inspected or mocked.
- **No imports needed in callers:** `open_object(item, config)` is the only public API. The caller doesn't need to know about specific opener implementations.

### Open All Defaults

```python
def open_defaults(project: Project, config: Config) -> None:
    """Open all objects marked as open_by_default, in display order."""
    for obj in project.objects:
        if obj.open_by_default:
            open_object(obj, config)
```

### Subprocess Calls and the UI

**subprocess.run() blocks.** For most operations (open URL, copy to clipboard), this is fine -- they complete in milliseconds. For iTerm2 AppleScript, which may take 100-500ms, use a Textual thread worker:

```python
# In the screen or widget that triggers operations
from textual import work

@work(thread=True)
def perform_open(self, item: ObjectItem, config: Config) -> None:
    """Run open_object in a thread to avoid blocking the UI."""
    open_object(item, config)
```

Use `thread=True` because `subprocess.run` is synchronous. The `@work` decorator ensures the UI remains responsive.

---

## Keyboard Binding Strategy

### Binding Hierarchy

Textual resolves key bindings by searching from the focused widget upward through the DOM to the App. joy should use this hierarchy deliberately:

| Level | Bindings | Purpose |
|-------|----------|---------|
| **App** | `q` (quit), `?` (help) | Always available, everywhere |
| **MainScreen** | `a` (add), `e` (edit), `d` (delete), `n` (new project), `s` (settings) | Available when main screen is active |
| **ProjectDetail** | `o` (open), `O` (open all), `space` (toggle default), arrow keys | Object-level operations, only when detail pane is focused |
| **ProjectList** | Arrow keys, `enter` | Navigation, only when list pane is focused |
| **Modals** | `enter` (confirm), `escape` (cancel) | Modal-specific, block everything below |

### Focus Management Between Panes

The two panes need clear focus semantics:

```python
# In MainScreen
BINDINGS = [
    ("h", "focus_list", "Focus List"),     # vim-style
    ("l", "focus_detail", "Focus Detail"), # vim-style
    ("left", "focus_list", "Focus List"),
    ("right", "focus_detail", "Focus Detail"),
    ("tab", "toggle_focus", "Switch Pane"),
]

def action_focus_list(self) -> None:
    self.query_one("#project-list").focus()

def action_focus_detail(self) -> None:
    self.query_one("#project-detail").focus()

def action_toggle_focus(self) -> None:
    if self.query_one("#project-list").has_focus:
        self.query_one("#project-detail").focus()
    else:
        self.query_one("#project-list").focus()
```

**Tab switches panes, not individual widgets.** Override the default Tab behavior (which cycles through all focusable widgets) to only toggle between the two panes. This keeps navigation predictable.

### Modal Screens for Destructive Actions

Use Textual's `ModalScreen` for confirmations and forms. ModalScreen blocks all input to the screen below:

```python
from textual.screen import ModalScreen

class ConfirmDeleteModal(ModalScreen[bool]):
    """Confirm before deleting a project or object."""

    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
```

Called from the screen:

```python
async def action_delete_object(self) -> None:
    confirmed = await self.app.push_screen_wait(
        ConfirmDeleteModal("Delete this object?")
    )
    if confirmed:
        # perform deletion
        ...
```

---

## Separation Between UI and Data/Operations

### The Rule

**Widgets and Screens never import `store` or `operations` directly.** They communicate through messages and the App/Screen acts as the mediator.

```
User presses 'o'
  -> ProjectDetail binding fires action_open_object
  -> ProjectDetail posts OpenObjectRequested message (bubbles up)
  -> MainScreen handles message, calls operations.open_object()
  -> MainScreen notifies user (toast/status)
```

This keeps widgets reusable and testable without TOML files or subprocess calls.

### Message Flow Example

```python
# In ProjectDetail widget
class OpenObjectRequested(Message):
    def __init__(self, item: ObjectItem) -> None:
        self.item = item
        super().__init__()

def action_open_object(self) -> None:
    selected = self._get_selected_object()
    if selected:
        self.post_message(self.OpenObjectRequested(selected))


# In MainScreen
@on(ProjectDetail.OpenObjectRequested)
@work(thread=True)
def handle_open_object(self, message: ProjectDetail.OpenObjectRequested) -> None:
    config = store.load_config()
    operations.open_object(message.item, config)
```

### Where State Lives

- **Source of truth:** The TOML files in `~/.joy/`.
- **In-memory state:** The MainScreen holds `projects: list[Project]` and `config: Config` loaded on mount. Modifications update both the in-memory list and persist via `store.save_projects()`.
- **Widgets receive data, don't own it.** ProjectList and ProjectDetail receive data through method calls or reactive attributes, not by loading it themselves.

```python
# MainScreen manages the data lifecycle
class MainScreen(Screen):
    def on_mount(self) -> None:
        self._config = store.load_config()
        self._projects = store.load_projects()
        self.query_one(ProjectList).set_projects(self._projects)
        if self._projects:
            self._select_project(self._projects[0])

    def _select_project(self, project: Project) -> None:
        detail = self.query_one(ProjectDetail)
        detail.project = project

    def _persist(self) -> None:
        store.save_projects(self._projects)
```

---

## Global Config vs. Per-Project Settings

### Clear Separation

| Setting | Location | Scope | Example |
|---------|----------|-------|---------|
| IDE | `config.toml` | Global | `ide = "PyCharm"` |
| Editor | `config.toml` | Global | `editor = "Sublime Text"` |
| Obsidian vault | `config.toml` | Global | `obsidian_vault = "wiki"` |
| Terminal | `config.toml` | Global | `terminal = "iTerm2"` |
| Default open kinds | `config.toml` | Global | `default_open_kinds = ["worktree", "agents"]` |
| Object list | `projects.toml` | Per-project | `[[project.object]]` entries |
| Open-by-default flags | `projects.toml` | Per-project | `open_by_default = true` per object |
| Project name, created | `projects.toml` | Per-project | `name = "joy"`, `created = 2026-04-10` |

### No Per-Project Config Overrides in v1

The PROJECT.md mentions "global default, overridable per project" for default open kinds. Implement this as:
- **On project creation:** The `default_open_kinds` from config.toml determines which object kinds get `open_by_default = true` initially.
- **After creation:** Each project's `open_by_default` flags are independent. No per-project config file.

This avoids a per-project config layer (which adds complexity). The user simply toggles `open_by_default` per object with the `space` key.

### Settings Screen

A dedicated `SettingsScreen` for editing global config. Pushed on top of MainScreen, popped when done. Uses standard Textual Input/Select widgets.

```python
class SettingsScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("enter", "save", "Save"),
    ]
    # Input fields for each config value
    # On save: update Config dataclass, call store.save_config()
```

---

## Build Order

Implementation should follow dependency order. Each phase builds on the previous and produces something testable.

### Phase 1: Foundation (No UI)
1. **`models.py`** -- Dataclasses for Project, ObjectItem, Config, enums
2. **`store.py`** -- TOML read/write functions
3. **`operations.py`** -- Type-dispatched openers
4. **Unit tests** for all three

_Testable without any TUI code. Verify data round-trips through TOML correctly. Verify each opener calls the right subprocess command._

### Phase 2: Basic TUI Shell
5. **`app.py`** -- JoyApp with MainScreen
6. **`widgets/project_list.py`** -- ProjectList with ListView
7. **`widgets/project_detail.py`** -- ProjectDetail showing objects
8. **`widgets/object_row.py`** -- ObjectRow rendering a single object
9. **`styles/`** -- CSS for two-pane layout

_Renders projects and objects. Navigation works. No mutations yet._

### Phase 3: Operations Integration
10. Wire `o` (open object) and `O` (open all defaults) to operations.py
11. Wire `space` (toggle open_by_default) with persist
12. Clipboard copy notification (toast)

_The core value proposition works: see projects, open artifacts._

### Phase 4: CRUD
13. **Add object** -- ObjectFormModal
14. **Edit object** -- Reuse ObjectFormModal
15. **Delete object** -- ConfirmDeleteModal
16. **New project** -- ProjectFormModal
17. **Delete project** -- ConfirmDeleteModal

_Full create/read/update/delete for projects and objects._

### Phase 5: Polish
18. **Settings screen**
19. **Icons per object type** (Textual supports Unicode emoji/icons)
20. **Visual polish** -- borders, colors, spacing
21. **Error handling** -- missing config, invalid TOML, subprocess failures

### Dependency Graph

```
models.py        (no deps)
    |
    +-- store.py        (depends on models)
    +-- operations.py   (depends on models)
    |
    +-- widgets/*       (depends on models)
    |       |
    |       +-- screens/*   (depends on widgets, store, operations)
    |               |
    |               +-- app.py   (depends on screens)
```

---

## Key Findings

1. **Textual's compose + message-bubbling architecture maps perfectly to joy's needs.** The two-pane layout uses dock-left for the project list and `1fr` width for the detail pane. ListView handles project navigation with built-in keyboard bindings. Custom messages bubble from widgets to screens, keeping the wiring clean. This is not a forced fit -- Textual was designed for exactly this kind of app.

2. **The two-level type system (PresetKind + ObjectType) is the critical design insight.** PresetKind is user-facing (9 values: mr, branch, ticket, etc.), ObjectType is operation-facing (6 values: URL, STRING, FILE, etc.). This decoupling means adding new preset kinds (e.g., "design" for Figma URLs) requires zero new operation code -- just an enum entry and a mapping. The operations layer stays at 6 handlers forever.

3. **Dict-based registry for type dispatch, not class hierarchy.** Each opener is a 3-5 line function. A class hierarchy (AbstractOpener, URLOpener, etc.) would be over-engineered for functions this simple. The `@opener(ObjectType.URL)` decorator pattern keeps registration co-located with implementation and makes the system trivially extensible.

4. **Strict UI/data separation: Widgets post messages, Screens handle operations.** Widgets never import `store` or `operations`. They post messages like `OpenObjectRequested` that bubble to the Screen, which calls operations and persists changes. This keeps widgets testable without I/O and follows Textual's intended architecture.

5. **Two TOML files are the right choice over directory-per-project or a database.** The data volume is tiny (dozens of projects, <10KB total). A single `projects.toml` with `[[project]]` array-of-tables is human-readable, atomically writable, and trivially parseable. Split config.toml from projects.toml because they change at different rates and have different schemas.

---

## Sources

- Textual App guide: https://textual.textualize.io/guide/app/
- Textual Screens guide: https://textual.textualize.io/guide/screens/
- Textual Input/Bindings guide: https://textual.textualize.io/guide/input/
- Textual Widgets guide: https://textual.textualize.io/guide/widgets/
- Textual Layout guide: https://textual.textualize.io/guide/layout/
- Textual Events/Messages guide: https://textual.textualize.io/guide/events/
- Textual Reactivity guide: https://textual.textualize.io/guide/reactivity/
- Textual Actions guide: https://textual.textualize.io/guide/actions/
- Textual Workers guide: https://textual.textualize.io/guide/workers/
- Textual ListView widget: https://textual.textualize.io/widgets/list_view/
- Textual OptionList widget: https://textual.textualize.io/widgets/option_list/
- Anatomy of a Textual UI (blog): https://textual.textualize.io/blog/2024/09/15/anatomy-of-a-textual-user-interface/
- Python tomllib docs: https://docs.python.org/3/library/tomllib.html
- PEP 443 singledispatch: https://peps.python.org/pep-0443/
- Python Registry Pattern: https://dev.to/dentedlogic/stop-writing-giant-if-else-chains-master-the-python-registry-pattern-ldm
