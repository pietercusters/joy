# Phase 12: iTerm2 Integration & Terminal Pane - Research

**Researched:** 2026-04-13
**Domain:** iTerm2 Python API integration, Textual TUI pane with cursor navigation
**Confidence:** HIGH

## Summary

Phase 12 transforms the stub `TerminalPane` into a live, interactive pane displaying all active iTerm2 sessions with Claude agent detection. The implementation requires the `iterm2` PyPI package (v2.15), which communicates with iTerm2 over websockets using protobuf. The API provides session enumeration via `app.terminal_windows` -> `window.tabs` -> `tab.sessions`, and session variables (`jobName`, `path`, `name`) via `session.async_get_variable()`. Session activation uses `session.async_activate()`.

The critical technical challenge is threading: the `iterm2` package's module-level `run_until_complete()` calls `sys.exit(1)` on `ConnectionRefusedError`, which would kill the entire TUI. The solution is to call `Connection().run_until_complete()` (the instance method) directly, which re-raises exceptions without calling `sys.exit`, allowing the `@work(thread=True)` worker to catch them gracefully.

The navigation model replicates `ProjectDetail`'s proven `_cursor` / `_rows` / `--highlight` pattern exactly. Single-line `SessionRow` widgets display icon, session name, busy/waiting indicator, foreground process, and cwd. Sessions are grouped into "Claude" (top) and "Other" sections using the existing `GroupHeader` pattern.

**Primary recommendation:** Use `Connection().run_until_complete()` (instance method, NOT module-level function) for all iTerm2 API calls from background threads. This avoids the `sys.exit(1)` trap while maintaining the established `@work(thread=True)` pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use `iterm2` PyPI package as a **required** (not optional) third dependency. Add to `pyproject.toml`.
- **D-02:** Fetch sessions in a `@work(thread=True)` worker using `asyncio.run(main)` in the thread. The iterm2 package's `run_until_complete()` owns a short-lived event loop in the background thread.
- **D-03:** When iTerm2 Python API is inaccessible, catch exception and call `set_sessions(None)` -- pane shows "iTerm2 unavailable". Never crash.
- **D-04:** New `TerminalSession` dataclass in `models.py`: `session_id`, `session_name`, `foreground_process`, `cwd`. Pure data, no iterm2 objects.
- **D-05:** Single-line rows. Format: `[icon] [session_name] [busy/waiting] [process] [cwd]`. `height: 1`.
- **D-06:** Two groups: "Claude" (top) and "Other" (below). GroupHeaders omitted when group is empty.
- **D-07:** Nerd Font icon constants: `ICON_SESSION`, `ICON_CLAUDE`, busy `●`, waiting `○`.
- **D-08:** Claude detection: `foreground_process == "claude"` (case-sensitive exact match).
- **D-09:** Busy if foreground is `claude`; waiting if foreground is shell (`zsh`, `bash`, `fish`).
- **D-10:** Claude sessions: busy before waiting, then alphabetical by session name within each sub-group.
- **D-11:** Navigation follows `ProjectDetail` exactly: `_cursor`, `_rows`, `--highlight` CSS. `GroupHeader` rows NOT navigable.
- **D-12:** Enter: `session.async_activate()` in `@work(thread=True)` worker.
- **D-13:** Escape returns focus to previous pane in Tab order (Projects pane).
- **D-14:** When no sessions available, `_cursor = -1`, j/k/Enter are no-ops.
- **D-15:** `r` key and timer both refresh terminal sessions alongside worktrees. Independent workers.
- **D-16:** `TerminalPane.border_title` follows Phase 10 stale-indicator pattern.
- **D-17:** Scroll position preservation on refresh.

### Claude's Discretion
- Exact Nerd Font codepoints for `ICON_SESSION`, `ICON_CLAUDE`, busy/waiting glyphs.
- Whether `_load_terminal()` calls `iterm2.run_until_complete()` or uses `asyncio.run()` directly with the iterm2 connection API -- choose whatever is cleaner.
- Truncation strategy for long session names / cwd paths.
- Exact `TerminalSession` field names.

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TERM-01 | Terminal pane lists all active iTerm2 sessions with session name, foreground process, and working directory | iTerm2 Python API provides `session.async_get_variable("jobName")` for foreground process, `session.async_get_variable("path")` for cwd, `session.name` for session name. Enumeration via `app.terminal_windows` -> `window.tabs` -> `tab.sessions`. |
| TERM-02 | Claude agent sessions grouped at top with busy/waiting indicator | D-08/D-09: foreground process detection. `jobName == "claude"` means busy; shell process means waiting. Sorting: busy first, then waiting, alphabetical within. |
| TERM-03 | User can navigate sessions with j/k and press Enter to focus iTerm2 window | `session.async_activate(select_tab=True, order_window_front=True)` focuses the session's window/tab. Navigation via ProjectDetail `_cursor`/`_rows` pattern. |
| TERM-04 | Graceful "unavailable" message when iTerm2 Python API is inaccessible | Must use `Connection().run_until_complete()` (instance method) to avoid `sys.exit(1)`. Catch `ConnectionRefusedError` and any `Exception` in worker. |
| TERM-05 | Session data refreshes alongside worktree data on timer and `r` key | Independent `_load_terminal()` worker parallels `_load_worktrees()`. Both called from `action_refresh_worktrees()` and timer callback. |
| TERM-06 | Border title shows refresh timestamp with stale indicator | Replicates `WorktreePane.set_refresh_label()` pattern from Phase 10. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack**: Python only, managed with `uv` -- no other runtimes
- **Platform**: macOS only
- **Install target**: `uv tool install git+<repo>`
- **Config location**: `~/.joy/`
- **Design**: Minimalistic, snappy -- no heavy dependencies
- **TUI framework**: Textual 8.x
- **Data format**: TOML (tomllib + tomli_w)
- **macOS integration**: subprocess for system commands
- **Build backend**: hatchling
- **Node command**: Use `/Users/pieter/.nvm/versions/node/v22.17.1/bin/node` instead of bare `node`

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| iterm2 | 2.15 | iTerm2 session communication | Official iTerm2 Python API. Communicates via websocket + protobuf. Only way to get session-level data (foreground process, cwd, session list). [VERIFIED: PyPI `pip3 index versions iterm2`] |
| textual | >=8.2 | TUI framework | Already in use. Provides `@work(thread=True)`, Widget, Static, VerticalScroll, Binding. [VERIFIED: pyproject.toml] |

### Supporting (transitive, pulled by iterm2)
| Library | Version | Purpose | Impact |
|---------|---------|---------|--------|
| protobuf | >=7.34 | iTerm2 API serialization | ~429KB wheel. Required by iterm2 for API communication. [VERIFIED: `pip3 install --dry-run iterm2`] |
| websockets | >=16.0 | iTerm2 API transport | ~175KB wheel. WebSocket connection to iTerm2. [VERIFIED: `pip3 install --dry-run iterm2`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| iterm2 Python API | AppleScript only | AppleScript cannot get foreground process, cwd, or enumerate all sessions with split panes. Only option for session-level data. [CITED: CONTEXT.md D-01] |
| Connection().run_until_complete() | Module-level iterm2.run_until_complete() | Module-level function calls sys.exit(1) on ConnectionRefusedError -- would kill the TUI. Instance method re-raises instead. [VERIFIED: GitHub source gnachman/iTerm2 connection.py] |
| asyncio.run() in thread | Connection().run_until_complete() in thread | Both create a fresh event loop. Connection().run_until_complete() is cleaner because it handles websocket setup, connection lifecycle, and task cleanup internally. asyncio.run() would require manual Connection setup. |

**Installation (update to pyproject.toml):**
```toml
dependencies = [
    "tomli-w>=1.0",
    "textual>=8.2",
    "iterm2>=2.15",
]
```

## Architecture Patterns

### Recommended Project Structure
```
src/joy/
├── models.py              # Add TerminalSession dataclass
├── terminal_sessions.py   # NEW: fetch_sessions() -> list[TerminalSession] | None
├── app.py                 # Add _load_terminal() worker, extend refresh
├── widgets/
│   └── terminal_pane.py   # Replace stub with full implementation
```

### Pattern 1: Session Enumeration via iTerm2 Python API
**What:** Connect to iTerm2, traverse window/tab/session tree, extract variables
**When to use:** Every refresh cycle (timer + manual `r`)
**Example:**
```python
# Source: iTerm2 Python API docs + GitHub source analysis
import iterm2
from iterm2.connection import Connection

def fetch_sessions() -> list[TerminalSession] | None:
    """Fetch all iTerm2 sessions. Returns None if API unavailable."""
    sessions = []
    try:
        async def _main(connection):
            app = await iterm2.async_get_app(connection)
            for window in app.terminal_windows:
                for tab in window.tabs:
                    for session in tab.sessions:
                        job_name = await session.async_get_variable("jobName") or ""
                        cwd = await session.async_get_variable("path") or ""
                        sessions.append(TerminalSession(
                            session_id=session.session_id,
                            session_name=session.name or "",
                            foreground_process=job_name,
                            cwd=cwd,
                        ))
        # Use instance method to avoid sys.exit(1) on failure
        Connection().run_until_complete(_main, retry=False)
        return sessions
    except Exception:
        return None
```

### Pattern 2: Cursor Navigation (replicate ProjectDetail)
**What:** `_cursor: int`, `_rows: list[SessionRow]`, `--highlight` CSS class
**When to use:** Terminal pane keyboard navigation
**Example:**
```python
# Source: src/joy/widgets/project_detail.py lines 103-179
class TerminalPane(Widget, can_focus=True):
    BINDINGS = [
        Binding("escape", "focus_projects", "Back"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("j", "cursor_down", "Down"),
        Binding("enter", "focus_session", "Focus"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cursor: int = -1
        self._rows: list[SessionRow] = []
        self.border_title = "Terminal"
```

### Pattern 3: Background Worker with Graceful Failure
**What:** `@work(thread=True)` calling iTerm2 API, pushing data to UI via `call_from_thread`
**When to use:** Loading terminal sessions, activating sessions
**Example:**
```python
# Source: src/joy/app.py _load_worktrees pattern (lines 111-136)
@work(thread=True, exit_on_error=False)
def _load_terminal(self) -> None:
    from joy.terminal_sessions import fetch_sessions  # lazy import
    try:
        sessions = fetch_sessions()
        self.app.call_from_thread(self._set_terminal_sessions, sessions)
        self.app.call_from_thread(self._mark_terminal_refresh_success)
    except Exception:
        self.app.call_from_thread(self._set_terminal_sessions, None)
        self.app.call_from_thread(self._mark_terminal_refresh_failure)
```

### Anti-Patterns to Avoid
- **Using module-level `iterm2.run_until_complete()`:** Calls `sys.exit(1)` on connection failure, killing the entire TUI. Always use `Connection().run_until_complete()` instance method. [VERIFIED: GitHub source]
- **Leaking iterm2 objects out of terminal_sessions.py:** `TerminalSession` dataclass in models.py must hold only plain strings. Connection objects, Session objects, etc. stay inside the fetch module. [CITED: CONTEXT.md D-04]
- **Blocking the main event loop:** All iTerm2 API calls must happen in `@work(thread=True)` workers. The iterm2 package creates its own asyncio event loop via `asyncio.new_event_loop()` in the background thread. [VERIFIED: GitHub source connection.py]
- **Assuming GroupHeader is importable from project_detail:** WorktreePane already duplicates GroupHeader to avoid cross-widget coupling. TerminalPane should also define its own or import from a shared location. [VERIFIED: worktree_pane.py line 94]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session enumeration | Custom AppleScript + pgrep | `iterm2` package API | AppleScript can't enumerate split-pane sessions, can't get foreground process, can't get cwd. The API handles all of this. [CITED: CONTEXT.md D-01] |
| Websocket connection to iTerm2 | Manual websocket client | `Connection().run_until_complete()` | Handles authentication, protobuf serialization, event loop lifecycle, task cleanup. [VERIFIED: GitHub source] |
| Cursor navigation | Custom key handler | Replicate ProjectDetail pattern | Proven pattern already in codebase. Same `_cursor`/`_rows`/`--highlight`/`action_cursor_up/down`. [VERIFIED: project_detail.py] |
| Scroll preservation | Manual offset tracking | `scroll.scroll_y` save/restore | Same pattern as WorktreePane `set_worktrees()`. [VERIFIED: worktree_pane.py line 271] |

**Key insight:** The iTerm2 Python API is the only viable data source for session-level information (foreground process, working directory, split-pane enumeration). AppleScript can create/focus windows but cannot inspect session state.

## Common Pitfalls

### Pitfall 1: `sys.exit(1)` in module-level `run_until_complete`
**What goes wrong:** Application terminates when iTerm2 is not running or Python API is disabled
**Why it happens:** The module-level convenience function `iterm2.run_until_complete()` catches `ConnectionRefusedError` and calls `sys.exit(1)` instead of re-raising
**How to avoid:** Use `Connection().run_until_complete(coro, retry=False)` -- the instance method re-raises exceptions normally, allowing the worker to catch them and call `set_sessions(None)`
**Warning signs:** TUI crashes when iTerm2 is closed; test suite exits unexpectedly
[VERIFIED: GitHub source gnachman/iTerm2/connection.py]

### Pitfall 2: Event loop conflicts between Textual and iterm2
**What goes wrong:** `RuntimeError: This event loop is already running` or stale event loop state
**Why it happens:** Textual's main thread runs its own asyncio event loop. If iterm2 API calls happen on the main thread, event loops collide.
**How to avoid:** All iTerm2 calls in `@work(thread=True)` workers. The `Connection().run()` method calls `asyncio.new_event_loop()` + `asyncio.set_event_loop(loop)`, creating an isolated loop in the worker thread.
**Warning signs:** RuntimeError on first refresh, intermittent freezes
[VERIFIED: GitHub source connection.py run() method]

### Pitfall 3: `session.name` is an attribute, not a coroutine
**What goes wrong:** `await session.name` raises TypeError
**Why it happens:** Unlike `async_get_variable()` and `async_activate()`, `session.name` is a plain attribute set during initialization from the session title. It is NOT async.
**How to avoid:** Access `session.name` directly (no await). Use `await session.async_get_variable("jobName")` for variables that need API calls.
**Warning signs:** TypeError in fetch_sessions, sessions returning with empty names
[VERIFIED: GitHub source session.py -- `self.name = link.session.title`]

### Pitfall 4: Variables returning empty string / None for inactive sessions
**What goes wrong:** `jobName` or `path` returns empty string for sessions where the shell hasn't set them
**Why it happens:** `jobName` tracks the foreground process but may be empty briefly during session initialization. `path` requires the session to have reported its cwd.
**How to avoid:** Default to empty string and handle gracefully in display. Use `or ""` on all variable reads. Don't make Claude detection depend on `path` -- use `foreground_process` only.
**Warning signs:** Empty process names in session rows, missing cwd
[CITED: iTerm2 Variables documentation -- async_get_variable returns empty string if undefined]

### Pitfall 5: GroupHeader duplication vs shared import
**What goes wrong:** Import circular dependency or tight coupling between pane widgets
**Why it happens:** WorktreePane already duplicates GroupHeader from project_detail.py. Importing from one widget into another creates coupling.
**How to avoid:** Duplicate GroupHeader in terminal_pane.py (same CSS, same class) OR extract to a shared `widgets/common.py`. The codebase chose duplication for worktree_pane -- follow the same convention.
**Warning signs:** Circular imports at import time
[VERIFIED: worktree_pane.py line 94 comment: "Duplicated from project_detail to avoid cross-widget coupling"]

### Pitfall 6: iTerm2 Python API prerequisite not communicated
**What goes wrong:** User installs joy, Terminal pane always shows "unavailable"
**Why it happens:** The Python API must be explicitly enabled in iTerm2: Preferences > General > Magic > "Enable Python API"
**How to avoid:** Document prerequisite clearly. Phase 13 README should cover this. The unavailable state message could hint at the fix.
**Warning signs:** Terminal pane permanently shows "unavailable" despite iTerm2 running
[CITED: iterm2.com/python-api-auth.html]

## Code Examples

### Complete fetch_sessions() Module
```python
# Source: Verified iTerm2 Python API session.html, connection.py, variables.html
"""Fetch active iTerm2 sessions via the Python API."""
from __future__ import annotations

from joy.models import TerminalSession

# Shell processes that indicate an idle/waiting Claude session
_SHELL_PROCESSES = frozenset({"zsh", "bash", "fish"})


def fetch_sessions() -> list[TerminalSession] | None:
    """Return all active iTerm2 sessions, or None if API unavailable.

    Uses Connection().run_until_complete() (instance method) to avoid
    the module-level function's sys.exit(1) on ConnectionRefusedError.
    """
    import iterm2  # lazy import -- heavy due to protobuf
    from iterm2.connection import Connection

    results: list[TerminalSession] = []

    async def _enumerate(connection):
        app = await iterm2.async_get_app(connection)
        for window in app.terminal_windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    job = await session.async_get_variable("jobName") or ""
                    cwd = await session.async_get_variable("path") or ""
                    results.append(TerminalSession(
                        session_id=session.session_id,
                        session_name=session.name or "",
                        foreground_process=job,
                        cwd=cwd,
                    ))

    try:
        Connection().run_until_complete(_enumerate, retry=False)
        return results
    except Exception:
        return None
```

### TerminalSession Dataclass
```python
# Source: CONTEXT.md D-04
@dataclass
class TerminalSession:
    """An active iTerm2 terminal session. Pure data, no iterm2 objects."""
    session_id: str
    session_name: str
    foreground_process: str
    cwd: str
```

### Session Activation (Enter key handler)
```python
# Source: iTerm2 Python API session.html async_activate
def _activate_session(session_id: str) -> bool:
    """Focus an iTerm2 session by ID. Returns True on success."""
    import iterm2
    from iterm2.connection import Connection

    success = False

    async def _focus(connection):
        nonlocal success
        app = await iterm2.async_get_app(connection)
        session = app.get_session_by_id(session_id)
        if session:
            await session.async_activate(select_tab=True, order_window_front=True)
            await app.async_activate()
            success = True

    try:
        Connection().run_until_complete(_focus, retry=False)
    except Exception:
        pass
    return success
```

### Claude Detection and Sorting Logic
```python
# Source: CONTEXT.md D-08, D-09, D-10
def is_claude_session(session: TerminalSession) -> bool:
    """D-08: Exact match on foreground_process."""
    return session.foreground_process == "claude"

def is_claude_busy(session: TerminalSession) -> bool:
    """D-09: Busy when claude is the foreground process."""
    return session.foreground_process == "claude"

def is_claude_waiting(session: TerminalSession) -> bool:
    """D-09: Waiting when shell is foreground (Claude session at idle prompt)."""
    return session.foreground_process in _SHELL_PROCESSES

def sort_sessions(sessions: list[TerminalSession]) -> tuple[list[TerminalSession], list[TerminalSession]]:
    """D-10: Split into Claude (busy first, then waiting, alpha) and Other (alpha)."""
    claude = [s for s in sessions if is_claude_session(s) or
              (s.foreground_process in _SHELL_PROCESSES and _was_claude_session(s))]
    other = [s for s in sessions if s not in claude]
    # ... sorting logic
```

**Note on Claude detection:** The context decision D-08 says `foreground_process == "claude"` classifies a session as Claude. D-09 adds that when the foreground process is a shell (`zsh`/`bash`/`fish`), the session is "waiting". The challenge is: how do we know a session *was* a Claude session if the foreground process is now a shell? The approach should be: classify based on `foreground_process` at the time of the snapshot. A session with `foreground_process == "claude"` is Claude-busy. A session whose `foreground_process` is a shell is simply "Other" -- unless we have another signal. The session name convention could help but D-08 explicitly says "No session-name convention required." This means the "waiting" state is only visible if the user has a session where Claude was running but returned to the shell prompt -- the session name might contain "claude" but that's not the detection mechanism. **Recommendation: only sessions with `foreground_process == "claude"` appear in the Claude group. Sessions where Claude exited and the shell resumed appear in "Other".** This is the simplest interpretation that matches D-08's explicit "exact match" rule.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AppleScript for all iTerm2 automation | Python API for data, AppleScript for window creation | iTerm2 3.3 (2019) | Python API gives session-level access AppleScript cannot |
| iterm2 package v1.x | iterm2 v2.15 | April 2026 | Latest API version, supports current iTerm2 |
| `iterm2.run_until_complete()` for scripts | `Connection().run_until_complete()` for embedded use | Always available | Instance method avoids sys.exit(1) |

**Deprecated/outdated:**
- AppleScript API for iTerm2: "Bug fixes only, no new features" per CLAUDE.md. Still works for window create/focus but cannot enumerate sessions or read variables.
- iTerm2 package v1.x: Older API surface. v2.15 is current.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `tab.sessions` returns all sessions including split panes (not just `current_session`) | Architecture Patterns | If it only returns current session, split-pane sessions would be invisible. Mitigation: also traverse via `tab.root` splitter tree. |
| A2 | `session.name` is set to something meaningful (not always empty) | Code Examples | If session names are frequently empty, the display would be unhelpful. Mitigation: fall back to showing foreground_process + cwd as the primary identifier. |
| A3 | The "waiting" Claude indicator (D-09) means sessions where Claude CLI returned to shell prompt will appear in the "Other" group since `foreground_process` is now the shell | Code Examples | If the user expects all Claude-related sessions (including idle ones) grouped together, they'd need a different detection mechanism (e.g., session name convention). The current D-08 rule is unambiguous -- only exact match on "claude". |

## Open Questions

1. **Claude "waiting" detection without session name convention**
   - What we know: D-08 says `foreground_process == "claude"` is the classifier. D-09 says shell as foreground means "waiting." But D-08 also says "No session-name convention required."
   - What's unclear: How to identify a session as "Claude waiting" when the foreground process is `zsh`/`bash`/`fish` -- there's no way to distinguish a Claude idle session from a regular terminal session without a naming convention or historical tracking.
   - Recommendation: For now, only `foreground_process == "claude"` sessions appear in the Claude group (all busy). If users want idle Claude sessions grouped, a future enhancement could use session name matching or a user-set variable. The CONTEXT.md D-09 may only apply when `foreground_process` toggles between `claude` and shell -- meaning we catch the "waiting" state on the next refresh after Claude exits. This is the most pragmatic interpretation.

2. **Import weight of iterm2 + protobuf on startup time**
   - What we know: iterm2 pulls in protobuf (~429KB) and websockets (~175KB). Joy's startup budget is 350ms.
   - What's unclear: Exact import time impact.
   - Recommendation: Use lazy imports (`from joy.terminal_sessions import ...` inside the worker function). The iterm2 package is only imported when the background thread runs, never on the import path of `joy.app`. This preserves startup time. [VERIFIED: existing pattern in app.py -- all heavy imports are inside worker functions]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-asyncio 0.25+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_terminal_pane.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TERM-01 | fetch_sessions returns list with session_id, session_name, foreground_process, cwd | unit (mocked iterm2) | `uv run pytest tests/test_terminal_sessions.py::test_fetch_sessions_success -x` | Wave 0 |
| TERM-01 | TerminalPane.set_sessions renders SessionRow for each session | unit (Textual pilot) | `uv run pytest tests/test_terminal_pane.py::test_set_sessions_renders_rows -x` | Wave 0 |
| TERM-02 | Claude sessions grouped before Other sessions | unit | `uv run pytest tests/test_terminal_pane.py::test_claude_group_at_top -x` | Wave 0 |
| TERM-02 | Busy Claude before waiting Claude within group | unit | `uv run pytest tests/test_terminal_pane.py::test_claude_busy_before_waiting -x` | Wave 0 |
| TERM-03 | Enter key calls async_activate on highlighted session | unit (mocked) | `uv run pytest tests/test_terminal_pane.py::test_enter_activates_session -x` | Wave 0 |
| TERM-03 | j/k navigation moves cursor through SessionRow widgets | unit (Textual pilot) | `uv run pytest tests/test_terminal_pane.py::test_jk_navigation -x` | Wave 0 |
| TERM-04 | fetch_sessions returns None when iTerm2 unavailable | unit (mocked exception) | `uv run pytest tests/test_terminal_sessions.py::test_fetch_sessions_unavailable -x` | Wave 0 |
| TERM-04 | set_sessions(None) shows "iTerm2 unavailable" message | unit (Textual pilot) | `uv run pytest tests/test_terminal_pane.py::test_unavailable_state -x` | Wave 0 |
| TERM-05 | _load_terminal called on r key and timer | integration (mock) | `uv run pytest tests/test_terminal_pane.py::test_refresh_loads_terminal -x` | Wave 0 |
| TERM-06 | border_title updates with timestamp and stale indicator | unit | `uv run pytest tests/test_terminal_pane.py::test_refresh_label -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_terminal_pane.py tests/test_terminal_sessions.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_terminal_sessions.py` -- covers TERM-01 (fetch), TERM-04 (unavailable)
- [ ] `tests/test_terminal_pane.py` -- covers TERM-01 (rendering), TERM-02 (grouping), TERM-03 (navigation), TERM-04 (unavailable state), TERM-05 (refresh), TERM-06 (label)

## iTerm2 Python API Reference

### Key Session Variables
| Variable | Access | Description | Requires Shell Integration |
|----------|--------|-------------|---------------------------|
| `jobName` | `await session.async_get_variable("jobName")` | Name of foreground process (e.g., "vim", "claude", "zsh") | No [VERIFIED: iterm2.com/documentation-variables.html] |
| `path` | `await session.async_get_variable("path")` | Current working directory | No (locally), Yes (over SSH) [VERIFIED: iterm2.com/documentation-variables.html] |
| `commandLine` | `await session.async_get_variable("commandLine")` | Full command line of foreground job | No [VERIFIED: iterm2.com/3.3/documentation-variables.html] |
| `name` | `session.name` (attribute, NOT async) | Session display name | No [VERIFIED: GitHub source session.py] |
| `session_id` | `session.session_id` (property) | Globally unique session ID | No [VERIFIED: GitHub source session.py] |

### Key Methods
| Method | Signature | Description |
|--------|-----------|-------------|
| `async_get_app` | `await iterm2.async_get_app(connection)` | Get App singleton for window/tab/session traversal |
| `async_activate` (Session) | `await session.async_activate(select_tab=True, order_window_front=True)` | Focus session's tab and bring window to front |
| `async_activate` (App) | `await app.async_activate()` | Bring iTerm2 app to foreground |
| `Connection().run_until_complete` | `Connection().run_until_complete(coro, retry=False)` | Run async function with managed connection lifecycle |

### Traversal Pattern
```
app.terminal_windows -> [Window]
  window.tabs -> [Tab]
    tab.sessions -> [Session]  # includes split panes
```

### Prerequisites
1. iTerm2 must be running
2. Python API must be enabled: Preferences > General > Magic > "Enable Python API"
3. `iterm2` package installed (pulled via joy's dependencies)

## Sources

### Primary (HIGH confidence)
- [iTerm2 Python API Session docs](https://iterm2.com/python-api/session.html) -- Session class properties and methods, async_activate, async_get_variable
- [iTerm2 Python API App docs](https://iterm2.com/python-api/app.html) -- App class, terminal_windows, get_session_by_id
- [iTerm2 Python API Connection docs](https://iterm2.com/python-api/connection.html) -- Connection class, run_until_complete
- [iTerm2 Python API Tab docs](https://iterm2.com/python-api/tab.html) -- Tab.sessions property, session tree traversal
- [iTerm2 Python API Window docs](https://iterm2.com/python-api/window.html) -- Window.tabs, async_activate
- [iTerm2 Variables Reference](https://iterm2.com/3.3/documentation-variables.html) -- Complete session variable list including jobName, path, commandLine
- [iTerm2 Scripting Fundamentals](https://iterm2.com/documentation-scripting-fundamentals.html) -- Variable context system, hostname/path/jobName
- [GitHub: gnachman/iTerm2 connection.py](https://github.com/gnachman/iTerm2/blob/master/api/library/python/iterm2/iterm2/connection.py) -- Source code confirming sys.exit(1) in module-level function, event loop creation in run()
- [GitHub: gnachman/iTerm2 session.py](https://github.com/gnachman/iTerm2/blob/master/api/library/python/iterm2/iterm2/session.py) -- session.name attribute, async_get_variable, async_activate
- [PyPI: iterm2](https://pypi.org/project/iterm2/) -- Version 2.15, dependencies (protobuf, websockets)
- [iTerm2 Python API Auth](https://iterm2.com/python-api-auth.html) -- Prerequisites for enabling Python API

### Secondary (MEDIUM confidence)
- [iTerm2 Variables docs (current)](https://iterm2.com/documentation-variables.html) -- Shell integration requirements for variables

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- iterm2 v2.15 verified on PyPI, API surface verified from official docs and GitHub source
- Architecture: HIGH -- replicates proven patterns from ProjectDetail, WorktreePane, and app.py workers
- Pitfalls: HIGH -- sys.exit(1) trap verified from source code; event loop isolation verified from Connection.run() implementation
- iTerm2 API: HIGH -- Session variables, activation, and traversal verified from official docs and GitHub source
- Claude detection: MEDIUM -- D-08/D-09 logic is straightforward, but "waiting" state detection (A3) has an ambiguity worth flagging

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable -- iTerm2 API changes slowly, iterm2 package last released April 2026)
