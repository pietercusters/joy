# Architecture Research: joy v1.1 Workspace Intelligence

**Project:** joy -- keyboard-driven Python TUI for managing coding project artifacts
**Researched:** 2026-04-13
**Overall confidence:** HIGH (layout, background polling), MEDIUM (iTerm2 Python API integration)

---

## Executive Summary

v1.1 transforms joy from a static artifact launcher into a live workspace dashboard. This requires three architectural additions: (1) a 2x2 CSS grid layout replacing the current Horizontal container, (2) a background data layer using Textual's `set_interval` + async workers for periodic git/CLI fetching, and (3) an iTerm2 Python API connection running within Textual's asyncio event loop via `Connection.async_create()`. The existing v1.0 components (ProjectList, ProjectDetail, models, store, operations) remain unchanged -- new code layers alongside them.

---

## 1. Layout Changes: 2x2 Grid

### Current Layout (v1.0)

```python
# app.py compose()
yield Header()
yield Horizontal(
    ProjectList(id="project-list"),      # width: 1fr
    ProjectDetail(id="project-detail"),  # width: 2fr
)
yield Footer()
```

CSS is inline in the `CSS` class variable. No `.tcss` file exists.

### Recommended Approach: CSS Grid on a Container Widget

**Use Textual's CSS Grid layout** on a container that wraps all four panes. Do NOT use nested Horizontal/Vertical containers -- CSS grid handles the 2x2 structure cleanly with fewer DOM nodes and better control over proportions.

```python
from textual.containers import Container

class JoyApp(App):
    CSS = """
    #pane-grid {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 1fr 2fr;
        grid-rows: 2fr 1fr;
        grid-gutter: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            ProjectList(id="project-list"),        # top-left
            ProjectDetail(id="project-detail"),    # top-right
            TerminalPane(id="terminal-pane"),       # bottom-left
            WorktreePane(id="worktree-pane"),       # bottom-right
            id="pane-grid",
        )
        yield Footer()
```

**Why CSS Grid over alternatives:**

| Approach | Verdict | Reason |
|----------|---------|--------|
| CSS Grid (`layout: grid`) | **Winner** | Native 2x2 with `grid-size: 2 2`. Column/row sizing via `grid-columns`/`grid-rows`. Single container, 4 children. Clean. |
| Nested Horizontal/Vertical | No | Requires `Vertical(Horizontal(A, B), Horizontal(C, D))` -- more DOM nodes, harder to control sizing ratios between rows. |
| Dock layout | No | Dock is for fixed position (top/bottom/left/right). Cannot express a 2x2 grid. |

**Grid sizing rationale:**
- `grid-columns: 1fr 2fr` -- preserves v1.0's existing width ratio (project list is narrower)
- `grid-rows: 2fr 1fr` -- top row (projects + detail) is the primary workspace; bottom row (terminals + worktrees) is auxiliary/glanceable
- `grid-gutter: 1` -- single line separator between panes for visual clarity

**Child ordering:** Textual CSS Grid fills cells left-to-right, top-to-bottom. The `compose()` yield order determines placement: first child = top-left, second = top-right, third = bottom-left, fourth = bottom-right.

### Confidence: HIGH
Verified via Textual official grid docs. `grid-size`, `grid-columns`, `grid-rows` are documented with `fr` unit support. This is the standard Textual pattern for multi-pane layouts.

---

## 2. Background Data Layer

### Problem

v1.0 has no background data fetching. All data is loaded once from TOML on startup (`_load_data`). v1.1 needs periodic polling of:
1. **Git worktrees** -- `git worktree list --porcelain` per registered repo
2. **Worktree dirty status** -- `git status --porcelain` per discovered worktree
3. **Branch remote tracking** -- `git for-each-ref --format='%(upstream)' refs/heads/<branch>` per worktree
4. **iTerm2 sessions** -- async queries via Python API (see Section 3)

### Recommended Pattern: `set_interval` + Async Worker

**Use `set_interval` on the App to trigger a periodic refresh, which dispatches an `@work(thread=True)` worker for git subprocess calls.**

```python
class JoyApp(App):
    _refresh_timer: Timer | None = None

    def on_mount(self) -> None:
        self._load_data()
        # Start background refresh engine (30s default, configurable)
        interval = self._config.refresh_interval  # new config field
        self._refresh_timer = self.set_interval(interval, self._refresh_workspace)

    def _refresh_workspace(self) -> None:
        """Periodic refresh callback -- dispatches worker."""
        self._fetch_worktrees_bg()
        self._fetch_terminals_bg()  # iTerm2 refresh (see Section 3)

    @work(thread=True, exclusive=True, exit_on_error=False)
    def _fetch_worktrees_bg(self) -> None:
        """Discover worktrees across all registered repos in a background thread."""
        from joy.workspace import discover_worktrees  # new module
        worktrees = discover_worktrees(self._config.repos)
        self.app.call_from_thread(self._update_worktrees, worktrees)

    def _update_worktrees(self, worktrees: list[WorktreeInfo]) -> None:
        """Push fetched worktree data to the pane (main thread)."""
        self.query_one(WorktreePane).set_worktrees(worktrees)
```

**Why this pattern:**

| Pattern | Verdict | Reason |
|---------|---------|--------|
| `set_interval` + `@work(thread=True)` | **Winner** | `set_interval` handles timing. Thread worker handles blocking subprocess calls. `exclusive=True` cancels stale fetches. `call_from_thread` safely pushes results to UI. |
| `@work` with `while True` + `asyncio.sleep` | No | Async workers cannot run blocking subprocess calls without thread pool. Mixing `await asyncio.sleep` with `subprocess.run` is wrong. |
| `set_interval` calling sync code directly | No | `set_interval` callbacks run on the main thread. Subprocess calls would block the UI. Must dispatch to worker. |
| Standalone `asyncio.create_task` | No | Bypasses Textual's worker lifecycle management. Workers auto-cancel on widget removal. Raw tasks do not. |

**`exclusive=True` is critical:** If a refresh takes longer than the interval (e.g., network latency on `gh`/`glab` CLI), the next trigger would start a second concurrent worker. `exclusive=True` cancels the previous worker before starting the new one, preventing resource buildup.

**Manual refresh (`r` keybinding):** The same `_refresh_workspace` method handles both periodic and manual refresh. The `r` binding simply calls it directly, and `exclusive=True` ensures any in-flight worker is cancelled.

### Timer Lifecycle

The `set_interval` returns a `Timer` object supporting `pause()`, `resume()`, `reset()`, and `stop()`. Use this for:
- Pausing refresh when a modal is open (save cycles)
- Resuming on modal dismiss
- Adjusting interval if user changes settings

### Git Subprocess Strategy

All git operations are **blocking subprocess calls** (`subprocess.run`), which is why they run in `@work(thread=True)` workers:

```python
# workspace.py (new module)
def discover_worktrees(repos: list[RepoConfig]) -> list[WorktreeInfo]:
    """Discover all worktrees across registered repos."""
    results = []
    for repo in repos:
        raw = subprocess.run(
            ["git", "-C", repo.local_path, "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        worktrees = _parse_worktree_porcelain(raw.stdout)
        for wt in worktrees:
            wt.dirty = _check_dirty(wt.path)
            wt.has_remote = _check_remote_tracking(wt.path, wt.branch)
            wt.repo_name = repo.name
        results.extend(worktrees)
    return results

def _check_dirty(worktree_path: str) -> bool:
    """Check if worktree has uncommitted changes."""
    result = subprocess.run(
        ["git", "-C", worktree_path, "status", "--porcelain"],
        capture_output=True, text=True, timeout=5
    )
    return bool(result.stdout.strip())

def _check_remote_tracking(worktree_path: str, branch: str) -> bool:
    """Check if branch has a remote tracking branch."""
    result = subprocess.run(
        ["git", "-C", worktree_path, "for-each-ref",
         f"--format=%(upstream)", f"refs/heads/{branch}"],
        capture_output=True, text=True, timeout=5
    )
    return bool(result.stdout.strip())
```

**Timeouts are mandatory.** Network-mounted filesystems or large repos can hang git commands. 10s for `worktree list`, 5s for status checks.

### Confidence: HIGH
`set_interval` and `@work(thread=True)` are both documented Textual 8.x patterns. The thread worker + `call_from_thread` bridge is the official pattern for blocking I/O in Textual apps.

---

## 3. iTerm2 Python API Integration

### The Challenge

The `iterm2` Python package (v2.15, released 2026-04-12) uses **asyncio websockets** to communicate with iTerm2. Textual itself runs on asyncio. The key question: can both coexist on the same event loop?

### Answer: Yes, via `Connection.async_create()`

The iTerm2 `Connection` class provides two usage modes:

1. **`run_until_complete()` / `run_forever()`** -- creates its own `asyncio.new_event_loop()`. **Cannot use** -- would conflict with Textual's loop.
2. **`Connection.async_create()`** -- "constructs a new connection and returns it without creating an asyncio event loop." Uses `asyncio.get_running_loop()` to attach to the current loop. **This is what we need.**

### Recommended Pattern: Async Worker for Connection

```python
class JoyApp(App):
    _iterm_connection: iterm2.Connection | None = None

    @work(exclusive=True, exit_on_error=False)
    async def _connect_iterm2(self) -> None:
        """Establish iTerm2 Python API connection within Textual's event loop."""
        import iterm2
        try:
            connection = await iterm2.Connection.async_create()
            self._iterm_connection = connection
        except Exception:
            self._iterm_connection = None
            self.notify("iTerm2 connection failed", severity="warning")

    @work(exclusive=True, exit_on_error=False)
    async def _fetch_terminals_bg(self) -> None:
        """Query iTerm2 for current session state."""
        if self._iterm_connection is None:
            return
        import iterm2
        try:
            app = await iterm2.async_get_app(self._iterm_connection)
            sessions = _extract_session_info(app)
            self.call_from_thread(self._update_terminals, sessions)
        except Exception:
            # Connection may have dropped -- attempt reconnect
            self._iterm_connection = None
            self._connect_iterm2()
```

**Important:** `_fetch_terminals_bg` uses an **async worker** (no `thread=True`), not a thread worker. The iTerm2 API is async-native and must run on the asyncio loop, not in a thread. Textual's async workers run as `asyncio.Task` objects on the same loop as the app.

However, `call_from_thread` is only for thread workers. For async workers, you can directly mutate the UI since you're already on the main thread:

```python
    @work(exclusive=True, exit_on_error=False)
    async def _fetch_terminals_bg(self) -> None:
        """Query iTerm2 for current session state."""
        if self._iterm_connection is None:
            return
        import iterm2
        try:
            app = await iterm2.async_get_app(self._iterm_connection)
            sessions = _extract_session_info(app)
            # Async workers run on the main thread -- safe to update UI directly
            self.query_one(TerminalPane).set_sessions(sessions)
        except Exception:
            self._iterm_connection = None
            self._connect_iterm2()
```

### iTerm2 Session Variables Available

The Python API exposes session variables via `session.async_get_variable(name)`:

| Variable | Description | Requires Shell Integration |
|----------|-------------|---------------------------|
| `jobName` | Foreground process name (e.g., "vim", "python") | No |
| `commandLine` | Full command line of foreground job | No |
| `jobPid` | PID of foreground job | No |
| `path` | Current working directory | Yes (without SSH) |
| `name` | Session name as shown in tab bar | No |
| `autoName` | Auto-generated session name | No |
| `hostname` | Current hostname | Yes |
| `username` | Current username | Yes |
| `lastCommand` | Last command run | Yes |

**Claude busy/waiting detection strategy:**
- Check `jobName` -- if it contains "claude" or "anthropic", the session is running a Claude agent
- Check `commandLine` for patterns like `claude`, `cursor`, known agent process names
- A session showing a shell prompt (jobName = "zsh"/"bash") with no long-running command is "idle"

### iTerm2 API Dependency Impact

Adding `iterm2` to `pyproject.toml` brings in:
- `websockets` (async websocket client)
- `protobuf` (Google protobuf for message serialization)

This is a meaningful dependency increase. Mitigation: **make iTerm2 integration optional.** If the `iterm2` package is not installed, the TerminalPane shows a helpful message ("Install iterm2 package for terminal integration") and the refresh engine skips terminal fetching.

```python
try:
    import iterm2
    HAS_ITERM2 = True
except ImportError:
    HAS_ITERM2 = False
```

**iTerm2 API server must be enabled:** Users must enable "Enable Python API" in iTerm2 > Settings > General > Magic. Document this in README.

### Connection Lifecycle

1. **On app mount:** Attempt `_connect_iterm2()` (fire-and-forget async worker)
2. **On each refresh cycle:** If connection exists, query sessions. If query fails, set connection to None.
3. **On next refresh after failure:** Re-attempt connection.
4. **On app exit:** Connection is garbage collected. No explicit cleanup needed (websocket closes).

### Confidence: MEDIUM
`Connection.async_create()` is documented for REPL usage but not explicitly for "embedding in another asyncio framework." The pattern is sound (it just calls `asyncio.get_running_loop()`), but there could be edge cases with Textual's asyncio management. Recommend early prototyping of the iTerm2 connection before building the full pane.

---

## 4. Reactive Data Flow

### Problem

Fetched data (worktrees, terminal sessions) must update pane widgets without full re-render of the entire app. Three patterns are available in Textual.

### Recommended: Direct Widget Method Calls (Same as v1.0)

v1.0 already established the pattern: `ProjectList.set_projects(projects)` clears and rebuilds the list. This works. Use the same pattern for the new panes.

```python
class WorktreePane(Widget):
    def set_worktrees(self, worktrees: list[WorktreeInfo]) -> None:
        """Update displayed worktrees. Called from refresh callback."""
        scroll = self.query_one("#worktree-scroll")
        scroll.remove_children()
        for wt in worktrees:
            scroll.mount(WorktreeRow(wt))

class TerminalPane(Widget):
    def set_sessions(self, sessions: list[SessionInfo]) -> None:
        """Update displayed terminal sessions. Called from refresh callback."""
        scroll = self.query_one("#terminal-scroll")
        scroll.remove_children()
        for session in sessions:
            scroll.mount(TerminalRow(session))
```

**Why NOT reactive attributes:**
- Reactive attributes trigger `render()` on the widget. But the panes contain child widgets (rows), not rendered text. Reactive recompose (`recompose=True`) would work but destroys and recreates all children -- equivalent to `remove_children()` + `mount()` but with more magic.
- Direct method calls are explicit, debuggable, and match v1.0 patterns. Consistency matters more than elegance.

**Why NOT `post_message`:**
- Messages bubble up the DOM tree. The data flow here is top-down (app pushes data to panes), not bottom-up (pane notifies app). Direct method calls are the correct pattern for parent-to-child data flow in Textual. The Textual docs explicitly state: "To update a child widget you get a reference to it and use it like any other Python object."

**Why NOT data binding:**
- Data binding connects reactive attributes between parent and child. The data here comes from a worker callback, not a reactive attribute chain. Binding would require storing worktrees/sessions as a reactive on the App, which adds indirection for no benefit.

### Incremental Updates (Optimization for Later)

The initial implementation should do full clear + rebuild on each refresh (30s interval makes this imperceptible). If profiling shows the rebuild is noticeable, switch to a diffing approach:

```python
def set_worktrees(self, worktrees: list[WorktreeInfo]) -> None:
    existing = {row.worktree.path: row for row in self._rows}
    new_paths = {wt.path for wt in worktrees}

    # Remove stale
    for path, row in existing.items():
        if path not in new_paths:
            row.remove()

    # Update existing or add new
    for wt in worktrees:
        if wt.path in existing:
            existing[wt.path].update_info(wt)  # in-place update
        else:
            self._scroll.mount(WorktreeRow(wt))
```

This is premature for v1.1. Implement only if needed.

### Last-Updated Indicator

The app should show when data was last refreshed. Use a reactive attribute on the pane or a simple Static widget:

```python
class WorktreePane(Widget):
    last_updated: reactive[str] = reactive("")

    def set_worktrees(self, worktrees: list[WorktreeInfo]) -> None:
        # ... rebuild rows ...
        from datetime import datetime
        self.last_updated = datetime.now().strftime("%H:%M:%S")

    def watch_last_updated(self, value: str) -> None:
        self.query_one("#last-updated", Static).update(f"Updated: {value}")
```

### Confidence: HIGH
Direct widget method calls for parent-to-child data flow is the established Textual pattern, documented and used throughout v1.0.

---

## 5. Data Model Changes

### New Models (models.py additions)

```python
@dataclass
class RepoConfig:
    """A registered repository in the repo registry."""
    name: str              # deduced or user-provided
    local_path: str        # absolute path to repo root
    remote_url: str = ""   # optional, for gh/glab detection
    branch_filter: str = "" # regex pattern to filter branches (e.g., "^feature/")

@dataclass
class WorktreeInfo:
    """Discovered worktree state (not persisted, in-memory only)."""
    path: str              # absolute worktree path
    branch: str            # branch name (or "detached")
    head: str              # HEAD commit SHA
    repo_name: str         # from RepoConfig
    dirty: bool = False    # has uncommitted changes
    has_remote: bool = True  # branch tracks a remote
    is_bare: bool = False
    is_detached: bool = False

@dataclass
class SessionInfo:
    """iTerm2 terminal session state (not persisted, in-memory only)."""
    session_id: str
    name: str              # session name / window name
    job_name: str = ""     # foreground process (e.g., "vim", "zsh")
    command_line: str = "" # full command line
    working_dir: str = ""  # current directory (requires shell integration)
    is_claude: bool = False  # detected Claude/AI agent session
    window_id: str = ""
    tab_id: str = ""
```

### Config Changes (config.toml)

```toml
# Existing fields (unchanged)
ide = "PyCharm"
editor = "Sublime Text"
obsidian_vault = ""
terminal = "iTerm2"
default_open_kinds = ["worktree", "agents"]

# New v1.1 fields
refresh_interval = 30  # seconds, minimum 10

# Repo registry
[[repos]]
name = "joy"
local_path = "/Users/pieter/Github/joy"
remote_url = "https://github.com/pietercusters/joy"
branch_filter = ""

[[repos]]
name = "other-project"
local_path = "/Users/pieter/Github/other"
remote_url = ""
branch_filter = "^(main|feature/)"
```

**Config dataclass update:**

```python
@dataclass
class Config:
    ide: str = "PyCharm"
    editor: str = "Sublime Text"
    obsidian_vault: str = ""
    terminal: str = "iTerm2"
    default_open_kinds: list[str] = field(default_factory=lambda: ["worktree", "agents"])
    # New v1.1 fields
    refresh_interval: int = 30
    repos: list[RepoConfig] = field(default_factory=list)
```

### Storage Strategy

| Data | Storage | Rationale |
|------|---------|-----------|
| Repo registry (`repos`) | `~/.joy/config.toml` | User-configured, persisted across sessions |
| Worktree discoveries | In-memory only | Ephemeral, changes every 30s, derived from git state |
| Terminal sessions | In-memory only | Ephemeral, changes every 30s, derived from iTerm2 state |
| Projects + objects | `~/.joy/projects.toml` (unchanged) | Unchanged from v1.0 |

**No new files needed for caching.** Worktree and terminal data is cheap to rediscover (subprocess calls take <1s for reasonable repo counts). Persisting it would add complexity for no benefit.

### TOML Schema for Repos (Array of Tables)

TOML's `[[repos]]` syntax (array of tables) maps naturally to `list[RepoConfig]`. `tomllib` parses this into a list of dicts. `tomli_w` writes it back. No schema changes needed.

### Confidence: HIGH
TOML array-of-tables is well-documented. In-memory-only for ephemeral data is the correct call for <10 repos.

---

## 6. New Components Map

### New Files

| File | Responsibility |
|------|---------------|
| `src/joy/widgets/worktree_pane.py` | WorktreePane widget: displays discovered worktrees with status indicators |
| `src/joy/widgets/worktree_row.py` | WorktreeRow widget: two-line row (branch + path, status indicators) |
| `src/joy/widgets/terminal_pane.py` | TerminalPane widget: displays iTerm2 sessions |
| `src/joy/widgets/terminal_row.py` | TerminalRow widget: session name + foreground process + directory |
| `src/joy/workspace.py` | Git worktree discovery: subprocess calls, porcelain parsing, dirty/remote checks |
| `src/joy/terminal.py` | iTerm2 API bridge: connection management, session querying, Claude detection |

### Modified Files

| File | Change |
|------|--------|
| `src/joy/app.py` | CSS Grid layout, `set_interval` timer, refresh dispatch, iTerm2 connection lifecycle, `r` keybinding |
| `src/joy/models.py` | Add `RepoConfig`, `WorktreeInfo`, `SessionInfo` dataclasses. Extend `Config` with `refresh_interval` and `repos` |
| `src/joy/store.py` | Handle `repos` array-of-tables in config load/save. Handle `refresh_interval`. |
| `src/joy/screens/settings.py` | Add repo registry UI (add/edit/remove repos), refresh interval setting |
| `pyproject.toml` | Add `iterm2` as optional dependency |

### Unchanged Files

| File | Why Unchanged |
|------|--------------|
| `src/joy/widgets/project_list.py` | Project list behavior is unchanged. Grouping by repo is a display concern, not a data model change. |
| `src/joy/widgets/project_detail.py` | Object detail pane is unchanged. |
| `src/joy/widgets/object_row.py` | Individual object rows unchanged. |
| `src/joy/operations.py` | Object open operations unchanged. |
| `src/joy/screens/confirmation.py` | Confirmation modal unchanged. |
| `src/joy/screens/name_input.py` | Name input modal unchanged. |
| `src/joy/screens/preset_picker.py` | Preset picker unchanged. |
| `src/joy/screens/value_input.py` | Value input modal unchanged. |

---

## 7. Data Flow Diagram (v1.1)

```
                    set_interval (30s)
                          |
                    _refresh_workspace()
                     /              \
                    v                v
    @work(thread=True)      @work(async)
    _fetch_worktrees_bg     _fetch_terminals_bg
    |                        |
    | subprocess.run         | await iterm2 API
    | git worktree list      | async_get_app()
    | git status --porcelain | session variables
    | git for-each-ref       |
    |                        |
    v                        v
    call_from_thread()       direct UI update (async worker = main thread)
    |                        |
    v                        v
    WorktreePane             TerminalPane
    .set_worktrees()         .set_sessions()
    |                        |
    v                        v
    remove_children()        remove_children()
    mount(WorktreeRow...)    mount(TerminalRow...)


    Store --reads/writes--> Config (with repos)
                              |
                              v
                        workspace.py (uses repos for git discovery)
                        terminal.py (uses iTerm2 API)
```

---

## 8. Focus and Keyboard Navigation

### Pane Focus Order

Tab/Shift+Tab should cycle through focusable panes. The natural order:

1. ProjectList (top-left) -- default focus on startup
2. ProjectDetail (top-right)
3. TerminalPane (bottom-left)
4. WorktreePane (bottom-right)

### Pane-Specific Bindings

| Pane | Key | Action |
|------|-----|--------|
| All panes | `r` | Manual refresh (priority binding on App) |
| WorktreePane | `Enter` | Open selected worktree in configured IDE |
| WorktreePane | `n` | Create new project from selected worktree |
| WorktreePane | `j/k` | Navigate worktree rows |
| TerminalPane | `Enter` | Focus selected iTerm2 session (bring to front) |
| TerminalPane | `j/k` | Navigate session rows |

### Sub-Title Update

The existing `on_descendant_focus` handler needs extension for the two new panes:

```python
def on_descendant_focus(self, event) -> None:
    node = event.widget
    while node is not None:
        if hasattr(node, "id"):
            if node.id == "project-detail":
                self.sub_title = "Detail"
                return
            if node.id in ("project-list", "project-listview"):
                self.sub_title = "Projects"
                return
            if node.id == "terminal-pane":
                self.sub_title = "Terminals"
                return
            if node.id == "worktree-pane":
                self.sub_title = "Worktrees"
                return
        node = node.parent
```

---

## 9. Build Order

Dependencies between components determine what must be built first.

### Phase 1: Foundation (No UI)

**Build: Data model + Config + Store updates**

- Add `RepoConfig`, `WorktreeInfo`, `SessionInfo` to `models.py`
- Extend `Config` with `refresh_interval` and `repos`
- Update `store.py` to load/save the new config fields
- Write tests for TOML round-trip with `[[repos]]`

**Rationale:** Everything else depends on these models. Zero UI risk. Can be tested in isolation.

### Phase 2: Git Worktree Discovery (No UI)

**Build: `workspace.py` module**

- `discover_worktrees(repos)` -- parse `git worktree list --porcelain`
- `_check_dirty(path)` -- `git status --porcelain`
- `_check_remote_tracking(path, branch)` -- `git for-each-ref`
- `_parse_worktree_porcelain(output)` -- porcelain format parser
- Unit tests with mocked subprocess

**Rationale:** Pure data-fetching logic. No Textual dependency. Testable with fixture data. Unblocks WorktreePane.

### Phase 3: Layout Change (Structural)

**Build: 2x2 CSS Grid layout**

- Change `app.py` compose to yield grid container with 4 children
- Create stub `WorktreePane` and `TerminalPane` (empty widgets with placeholder text)
- Verify layout renders correctly, focus cycling works, existing ProjectList + ProjectDetail behavior is unchanged

**Rationale:** The layout change touches the app's compose method. Doing this with stubs means any regressions in existing behavior are caught before new logic is added. This is the highest-risk structural change.

### Phase 4: WorktreePane (First New Pane)

**Build: `worktree_pane.py`, `worktree_row.py`**

- WorktreePane with `set_worktrees()`, cursor navigation (j/k), Enter to open in IDE
- WorktreeRow with two-line display: branch name (line 1), path + status indicators (line 2)
- Dirty indicator, no-remote indicator
- Branch filter pattern support (regex against `RepoConfig.branch_filter`)

**Rationale:** WorktreePane depends on Phase 1 (models) and Phase 2 (discovery). It's simpler than TerminalPane (no async API, no external connection). Build the simpler pane first to establish patterns.

### Phase 5: Background Refresh Engine

**Build: `set_interval` + worker dispatch in `app.py`**

- Wire `set_interval` to `_refresh_workspace()`
- Wire `_fetch_worktrees_bg()` thread worker to WorktreePane
- `r` keybinding for manual refresh
- Last-updated indicator on panes
- Timer pause/resume around modals

**Rationale:** Depends on WorktreePane existing (Phase 4) to verify the refresh actually updates the UI. Cannot be tested without a real pane to push data to.

### Phase 6: iTerm2 Integration

**Build: `terminal.py` module, iTerm2 connection in app**

- `Connection.async_create()` on mount
- Session querying via async worker
- Claude detection heuristic (jobName/commandLine matching)
- Graceful degradation when iterm2 package not installed
- Connection recovery on failure

**Rationale:** Highest-risk component (MEDIUM confidence on async integration). By building it last, the rest of the app works even if iTerm2 integration needs iteration. The TerminalPane stub from Phase 3 shows "No iTerm2 connection" until this phase completes.

### Phase 7: TerminalPane (Second New Pane)

**Build: `terminal_pane.py`, `terminal_row.py`**

- TerminalPane with `set_sessions()`, cursor navigation, Enter to focus session
- TerminalRow showing session name, foreground process, working directory, Claude indicator
- Wire to refresh engine

**Rationale:** Depends on Phase 6 (iTerm2 data) and Phase 5 (refresh engine). Cannot be meaningfully built without the data source.

### Phase 8: Settings + New Project from Worktree

**Build: Settings modal updates, worktree-to-project flow**

- Repo registry in settings modal (add/edit/remove)
- Refresh interval setting
- "New project from worktree" in new project modal -- pick a discovered worktree to pre-fill fields
- Project list grouping by repo + "Other" bucket

**Rationale:** Polish and integration features that depend on everything else working. Lowest risk, highest dependency count.

### Build Order Summary

```
Phase 1: Models + Config + Store
    |
Phase 2: workspace.py (git discovery)
    |
Phase 3: 2x2 Layout (stubs)
    |
Phase 4: WorktreePane (full)
    |
Phase 5: Refresh Engine
    |         \
Phase 6: terminal.py (iTerm2 API)
    |
Phase 7: TerminalPane (full)
    |
Phase 8: Settings + Project-from-Worktree
```

---

## 10. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| iTerm2 `Connection.async_create()` conflicts with Textual's event loop | Medium | Prototype in isolation first. Fall back to subprocess + osascript if async API fails. |
| iTerm2 Python API server not enabled by user | Low | Detect on connection failure, show clear error message with setup instructions. |
| `iterm2` package not installed | Low | Optional dependency with graceful degradation. TerminalPane shows install instructions. |
| Git subprocess calls hang on network mounts | Medium | Mandatory timeouts (5-10s) on all subprocess.run calls. Worker `exclusive=True` prevents buildup. |
| Layout change breaks existing ProjectList/ProjectDetail | Low | Phase 3 uses stubs so breakage is caught before new logic is added. Full test suite runs after layout change. |
| Refresh engine causes UI stutter | Low | Thread workers for blocking I/O, async workers for iTerm2. Main thread only does DOM updates. 30s interval means updates are infrequent. |
| Too many worktrees across repos makes pane unusable | Low | Branch filter patterns per repo. Users configure which branches to show. |

---

## Sources

### Textual (HIGH confidence)
- Grid layout: https://textual.textualize.io/styles/grid/
- Grid size: https://textual.textualize.io/styles/grid/grid_size/
- Grid rows: https://textual.textualize.io/styles/grid/grid_rows/
- Grid columns: https://textual.textualize.io/styles/grid/grid_columns/
- Layout guide: https://textual.textualize.io/guide/layout/
- Design a layout: https://textual.textualize.io/how-to/design-a-layout/
- Workers: https://textual.textualize.io/guide/workers/
- Reactivity: https://textual.textualize.io/guide/reactivity/
- Timer API: https://textual.textualize.io/api/timer/
- Events and messages: https://textual.textualize.io/guide/events/

### iTerm2 Python API (MEDIUM confidence)
- Connection class: https://iterm2.com/python-api/connection.html
- Connection source: https://github.com/gnachman/iTerm2/blob/master/api/library/python/iterm2/iterm2/connection.py
- Session API: https://iterm2.com/python-api/session.html
- App API: https://iterm2.com/python-api/app.html
- Variables reference: https://iterm2.com/3.3/documentation-variables.html
- Variables Python API: https://iterm2.com/python-api/variables.html
- Scripting fundamentals: https://iterm2.com/documentation-scripting-fundamentals.html
- PyPI: https://pypi.org/project/iterm2/

### Git (HIGH confidence)
- git-worktree: https://git-scm.com/docs/git-worktree
- git-status: https://git-scm.com/docs/git-status
- git-for-each-ref: https://git-scm.com/docs/git-for-each-ref
