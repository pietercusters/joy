---
phase: quick-260429-amk
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/joy/models.py
  - src/joy/terminal_sessions.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/screens/legend.py
  - src/joy/hooks.py
  - tests/test_terminal_sessions.py
  - tests/test_terminal_pane.py
  - tests/test_hooks.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "Claude sessions in TerminalPane show green filled circle when busy (running tools/thinking)"
    - "Claude sessions in TerminalPane show dim hollow circle when idle (at prompt)"
    - "Claude sessions in TerminalPane show yellow/orange filled circle when waiting for user input"
    - "Running 'joy setup-hooks' installs hook script and merges into ~/.claude/settings.json without destroying existing hooks"
    - "State files in ~/.joy/claude-states/ are created by hook events and read by joy on each refresh"
    - "When is_claude=False for a TTY, any stale state file for that TTY is ignored"
  artifacts:
    - path: "src/joy/models.py"
      provides: "TerminalSession.claude_state field"
      contains: "claude_state"
    - path: "src/joy/terminal_sessions.py"
      provides: "_read_claude_states() function and integration into fetch_sessions()"
      contains: "_read_claude_states"
    - path: "src/joy/widgets/terminal_pane.py"
      provides: "3-state color-coded indicators using claude_state"
      contains: "claude_state"
    - path: "src/joy/hooks.py"
      provides: "setup_hooks() function and hook script generation"
      contains: "setup_hooks"
    - path: "src/joy/screens/legend.py"
      provides: "Updated legend with waiting_input indicator"
      contains: "waiting_input"
  key_links:
    - from: "hook script (~/.joy/bin/claude-state-hook.sh)"
      to: "~/.joy/claude-states/{tty}.json"
      via: "atomic write (printf + mv -f)"
      pattern: "claude-states"
    - from: "src/joy/terminal_sessions.py"
      to: "~/.joy/claude-states/"
      via: "_read_claude_states() reads all JSON files"
      pattern: "_read_claude_states"
    - from: "src/joy/terminal_sessions.py"
      to: "src/joy/models.py"
      via: "populates TerminalSession.claude_state from state files"
      pattern: "claude_state=.*state_info"
    - from: "src/joy/widgets/terminal_pane.py"
      to: "src/joy/models.py"
      via: "reads session.claude_state for indicator rendering"
      pattern: "session\\.claude_state"
---

<objective>
Implement Claude Code agent state detection via hooks. Claude Code reports its own state (idle/busy/waiting_input) through hook events that write TTY-keyed JSON files. Joy reads these files during terminal refresh and displays distinct color-coded indicators in TerminalPane.

Purpose: Replace the binary busy/waiting heuristic (foreground_process check) with precise 3-state detection sourced directly from Claude Code events. Users can see at a glance which Claude agents need attention (waiting_input), which are working (busy), and which are ready for a new prompt (idle).

Output: Hook script, setup-hooks CLI command, state file reader, updated model/UI, comprehensive tests.
</objective>

<execution_context>
@.planning/quick/260429-amk-implement-claude-agent-status-detection-/260429-amk-CONTEXT.md
@.planning/quick/260429-amk-implement-claude-agent-status-detection-/260429-amk-RESEARCH.md
</execution_context>

<context>
@src/joy/models.py
@src/joy/terminal_sessions.py
@src/joy/widgets/terminal_pane.py
@src/joy/screens/legend.py
@src/joy/app.py
@tests/test_terminal_sessions.py
@tests/test_terminal_pane.py

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
    # NEW: claude_state: str | None = None  # "idle" | "busy" | "waiting_input" | None
```

From src/joy/terminal_sessions.py:
```python
_SHELL_PROCESSES = frozenset({"zsh", "bash", "fish", "sh", "dash"})

def fetch_sessions() -> tuple[list[TerminalSession], set[str]] | None:
    # Collects raw data from iTerm2 API, then builds TerminalSession objects
    # Integration point: read claude states BEFORE the sync loop, populate in loop

def _detect_claude(job: str, tty: str) -> bool:
    # Existing: returns True if claude process detected
```

From src/joy/widgets/terminal_pane.py:
```python
INDICATOR_BUSY = "\u25cf"    # BLACK CIRCLE -- session running claude
INDICATOR_WAITING = "\u25cb" # WHITE CIRCLE -- session at shell prompt

class SessionRow(Static):
    def __init__(self, session, *, is_claude=False, is_busy=False, show_shortcut=False, **kwargs)
    @staticmethod
    def _build_content(session, *, is_claude=False, is_busy=False, show_shortcut=False) -> Text

# In set_sessions(): is_busy computed as foreground_process.lower() not in _SHELL_PROCESSES
```

From src/joy/screens/legend.py:
```python
_TERMINAL_ICONS: list[tuple[str, str, str]] = [
    ("\uf120", "Terminal session", ""),
    ("\U000f1325", "Claude agent session", ""),
    ("\u25cf", "Claude busy (running)", "green"),
    ("\u25cb", "Claude waiting (at prompt)", "dim"),
]
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Model + State Reader + Hook Setup</name>
  <files>
    src/joy/models.py,
    src/joy/terminal_sessions.py,
    src/joy/hooks.py,
    tests/test_terminal_sessions.py,
    tests/test_hooks.py
  </files>
  <behavior>
    - TerminalSession.claude_state field: None by default, accepts "idle"|"busy"|"waiting_input"
    - _read_claude_states() returns dict mapping tty short name to state dict
    - _read_claude_states() handles missing dir, corrupt JSON, empty dir gracefully
    - fetch_sessions() populates claude_state from state files, only when is_claude=True
    - fetch_sessions() ignores state file when is_claude=False for that TTY (staleness rule)
    - setup_hooks() creates ~/.joy/bin/claude-state-hook.sh with correct content and +x
    - setup_hooks() merges hook into ~/.claude/settings.json for all 6 events
    - setup_hooks() preserves existing hooks (terminal-notifier etc)
    - setup_hooks() is idempotent (running twice produces same result)
    - Hook script parses hook_event_name and session_id from stdin JSON with shell builtins
    - Hook script walks process tree to find TTY, writes atomic state file
  </behavior>
  <action>
**1. Add `claude_state` to TerminalSession in `src/joy/models.py`:**

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

**2. Create `src/joy/hooks.py`:**

This module provides:
- `HOOK_SCRIPT_CONTENT`: string constant with the full bash hook script (from RESEARCH.md code example). The script:
  - Reads JSON from stdin
  - Parses `hook_event_name` and `session_id` using shell parameter expansion (no jq)
  - Walks process tree via `ps -o tty= -p $PID` to find ancestor with real TTY
  - Maps events to states: Stop/SessionStart->idle, UserPromptSubmit/PreToolUse->busy, Notification->waiting_input, SessionEnd->delete
  - Writes atomically via printf to .tmp then `mv -f`
  - State file path: `~/.joy/claude-states/{tty}.json`
  - Always exits 0

- `HOOK_EVENTS`: list of the 6 event names: `["Stop", "Notification", "UserPromptSubmit", "PreToolUse", "SessionStart", "SessionEnd"]`

- `HOOK_COMMAND`: the command string `"~/.joy/bin/claude-state-hook.sh"` (tilde is expanded by the shell at invocation time)

- `setup_hooks() -> None`: 
  1. Create `~/.joy/bin/` directory (mkdir -p)
  2. Write `HOOK_SCRIPT_CONTENT` to `~/.joy/bin/claude-state-hook.sh`
  3. Set executable bit: `os.chmod(path, 0o755)`
  4. Read `~/.claude/settings.json` (create if missing, with empty `{}`)
  5. For each event in HOOK_EVENTS:
     - If `hooks` key missing in settings, create it as empty dict
     - If event key missing in `hooks`, create: `[{"matcher": "", "hooks": [{"type": "command", "command": HOOK_COMMAND}]}]`
     - If event exists: find matcher group with `matcher: ""`. If found, check if HOOK_COMMAND already in its hooks array. If not, append. If no empty-matcher group, create one.
  6. Write settings.json back with `json.dump(indent=2)`
  7. Create `~/.joy/claude-states/` directory (mkdir -p)

- `_install_hook_script(joy_dir: Path) -> Path`: internal, takes joy_dir for testability
- `_merge_settings(settings_path: Path) -> None`: internal, takes path for testability

**3. Add `_read_claude_states()` to `src/joy/terminal_sessions.py`:**

```python
import json
from pathlib import Path

def _read_claude_states() -> dict[str, dict]:
    """Read all claude state files. Returns {tty_short: {"state": ..., "ts": ...}}."""
    state_dir = Path.home() / ".joy" / "claude-states"
    states = {}
    if not state_dir.is_dir():
        return states
    for f in state_dir.iterdir():
        if f.suffix == ".json" and not f.name.endswith(".tmp"):
            try:
                data = json.loads(f.read_text())
                tty = f.stem  # e.g., "ttys041"
                states[tty] = data
            except Exception:
                continue
    return states
```

**4. Integrate into `fetch_sessions()`:**

After `run_until_complete` returns and before/at the sync loop, read states once:

```python
claude_states = _read_claude_states()
```

In the loop building TerminalSession objects:
```python
for session_id, tab_id, name, job, cwd, tty in raw:
    is_claude = _detect_claude(job, tty)
    tty_short = tty.removeprefix("/dev/") if tty else ""
    # Only use hook state when is_claude=True (per CONTEXT.md staleness decision)
    state_info = claude_states.get(tty_short) if is_claude else None
    results.append(
        TerminalSession(
            session_id=session_id,
            session_name=name,
            foreground_process=job,
            cwd=cwd,
            tab_id=tab_id,
            is_claude=is_claude,
            claude_state=state_info.get("state") if state_info else None,
        )
    )
```

**5. Create `tests/test_hooks.py`:**

Test setup_hooks():
- `test_setup_hooks_creates_script_file`: Verify script file created at joy_dir/bin/claude-state-hook.sh
- `test_setup_hooks_script_is_executable`: Verify 0o755 permissions
- `test_setup_hooks_script_content_contains_state_dir`: Verify script content references claude-states
- `test_setup_hooks_merges_into_empty_settings`: Fresh settings.json gets all 6 events
- `test_setup_hooks_preserves_existing_hooks`: Existing terminal-notifier hooks survive
- `test_setup_hooks_idempotent`: Running twice produces identical settings.json
- `test_setup_hooks_creates_state_dir`: ~/.joy/claude-states/ directory created

All tests use tmp_path to avoid touching real ~/.joy or ~/.claude. Patch `Path.home()` to return tmp_path.

**6. Add tests to `tests/test_terminal_sessions.py`:**

New test class `TestReadClaudeStates`:
- `test_read_claude_states_returns_empty_when_no_dir`: No dir -> empty dict
- `test_read_claude_states_reads_valid_files`: Write sample JSON -> reads correctly
- `test_read_claude_states_skips_corrupt_json`: Invalid JSON -> skipped, others still read
- `test_read_claude_states_skips_tmp_files`: Files ending in .tmp are ignored

New test class `TestFetchSessionsClaudeState`:
- `test_fetch_sessions_populates_claude_state_from_hook_file`: Mock _read_claude_states -> verify claude_state on session
- `test_fetch_sessions_ignores_state_when_not_claude`: is_claude=False -> claude_state=None even if state file exists
- `test_fetch_sessions_claude_state_none_when_no_file`: No state file -> claude_state=None
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -m pytest tests/test_hooks.py tests/test_terminal_sessions.py -x -v 2>&1 | tail -40</automated>
  </verify>
  <done>
    - TerminalSession has claude_state field, defaults to None
    - _read_claude_states() reads ~/.joy/claude-states/*.json into a dict
    - fetch_sessions() populates claude_state from hook state files (only when is_claude=True)
    - hooks.py provides setup_hooks() that installs script + merges settings.json
    - All new tests pass; existing tests unbroken
  </done>
</task>

<task type="auto">
  <name>Task 2: UI Rendering + Legend + CLI Entry Point</name>
  <files>
    src/joy/widgets/terminal_pane.py,
    src/joy/screens/legend.py,
    src/joy/app.py,
    tests/test_terminal_pane.py
  </files>
  <action>
**1. Add `INDICATOR_WAITING_INPUT` constant to `src/joy/widgets/terminal_pane.py`:**

```python
INDICATOR_BUSY = "\u25cf"           # BLACK CIRCLE -- claude running
INDICATOR_WAITING = "\u25cb"        # WHITE CIRCLE -- claude idle (at prompt)
INDICATOR_WAITING_INPUT = "\u25cf"  # BLACK CIRCLE -- claude needs user input (yellow)
```

Note: INDICATOR_WAITING_INPUT uses the same glyph as INDICATOR_BUSY but will be styled yellow/orange instead of green. The style is applied in _build_content().

**2. Update `SessionRow._build_content()` to use `claude_state`:**

Change the signature to accept `claude_state: str | None = None` instead of `is_busy: bool = False`:

```python
@staticmethod
def _build_content(
    session: TerminalSession,
    *,
    is_claude: bool = False,
    claude_state: str | None = None,
    show_shortcut: bool = False,
) -> Text:
    t = Text(no_wrap=True, overflow="ellipsis")
    if is_claude:
        t.append(f" {ICON_CLAUDE} ", style="bold")
        t.append(session.session_name)
        if claude_state == "busy":
            t.append(f"  {INDICATOR_BUSY}", style="green")
        elif claude_state == "waiting_input":
            t.append(f"  {INDICATOR_WAITING_INPUT}", style="yellow")
        else:
            # "idle" or None (fallback)
            t.append(f"  {INDICATOR_WAITING}", style="dim")
        t.append(f"  {session.foreground_process}", style="dim")
    else:
        t.append(f" {ICON_SESSION} ", style="bold")
        t.append(session.session_name)
        t.append(f"  {session.foreground_process}", style="dim")
    # Abbreviated cwd
    cwd = _abbreviate_home(session.cwd)
    t.append(f"  {cwd}", style="dim")
    if show_shortcut:
        t.append("  [h]", style="dim")
    return t
```

Also update `SessionRow.__init__` to store `claude_state` instead of `is_busy`:

```python
def __init__(
    self,
    session: TerminalSession,
    *,
    is_claude: bool = False,
    claude_state: str | None = None,
    show_shortcut: bool = False,
    **kwargs,
) -> None:
    self.session_id = session.session_id
    self.session_name = session.session_name
    self._session = session
    self._is_claude = is_claude
    self._claude_state = claude_state
    self._show_shortcut = show_shortcut
    content = self._build_content(session, is_claude=is_claude, claude_state=claude_state, show_shortcut=show_shortcut)
    super().__init__(content, **kwargs)
```

**3. Update `set_sessions()` in TerminalPane:**

Replace the `is_busy` computation with `claude_state` resolution. In both the tab_groups loop and the Other loop:

```python
# Replace:
#   is_busy = session.foreground_process.lower() not in _SHELL_PROCESSES
#   row = SessionRow(session, is_claude=session.is_claude, is_busy=is_busy, ...)

# With:
if session.claude_state is not None:
    claude_state = session.claude_state  # direct from hook
elif session.is_claude:
    # Fallback heuristic when no hook state available
    claude_state = "busy" if session.foreground_process.lower() not in _SHELL_PROCESSES else "idle"
else:
    claude_state = None
row = SessionRow(session, is_claude=session.is_claude, claude_state=claude_state, show_shortcut=len(new_rows) == 0)
```

**4. Update `_sort_key()` in set_sessions():**

The sort key should use claude_state for ordering. Claude sessions needing attention should sort first:

```python
def _sort_key(s: TerminalSession) -> tuple[int, int, str]:
    """Sort: Claude-waiting_input first (0,0), Claude-busy (0,1), Claude-idle (0,2), other (1,x), then alpha."""
    if s.is_claude:
        if s.claude_state == "waiting_input":
            return (0, 0, s.session_name.lower())
        elif s.claude_state == "busy":
            return (0, 1, s.session_name.lower())
        elif s.claude_state == "idle":
            return (0, 2, s.session_name.lower())
        else:
            # Fallback: use heuristic
            is_busy = s.foreground_process.lower() not in _SHELL_PROCESSES
            return (0, 1 if is_busy else 2, s.session_name.lower())
    return (1, 0, s.session_name.lower())
```

**5. Update legend in `src/joy/screens/legend.py`:**

Update `_TERMINAL_ICONS` to include the new waiting_input state:

```python
_TERMINAL_ICONS: list[tuple[str, str, str]] = [
    ("\uf120", "Terminal session", ""),
    ("\U000f1325", "Claude agent session", ""),
    ("\u25cf", "Claude busy (running)", "green"),
    ("\u25cf", "Claude needs input", "yellow"),
    ("\u25cb", "Claude idle (at prompt)", "dim"),
]
```

**6. Add `setup-hooks` CLI command in `src/joy/app.py`:**

In the `main()` function, add handling before the TUI starts:

```python
def main() -> None:
    """Main entry point for the joy CLI."""
    if "--version" in sys.argv:
        print(f"joy {_get_version()}")
        return
    if "setup-hooks" in sys.argv:
        from joy.hooks import setup_hooks
        setup_hooks()
        print("Claude Code hooks installed successfully.")
        print("  Script: ~/.joy/bin/claude-state-hook.sh")
        print("  Config: ~/.claude/settings.json")
        return
    app = JoyApp()
    app.run()
```

**7. Update existing tests in `tests/test_terminal_pane.py`:**

Tests that use `is_busy=True` or `is_busy=False` in SessionRow must be updated to use `claude_state="busy"` or `claude_state="idle"` (or `claude_state=None`) respectively:

- `test_session_row_claude_busy_shows_indicator_busy`: Change `is_busy=True` -> `claude_state="busy"`
- `test_session_row_claude_waiting_shows_indicator_waiting`: Change `is_busy=False` -> `claude_state="idle"` (or `claude_state=None`)

Add new tests:
- `test_session_row_claude_waiting_input_shows_yellow_indicator`: SessionRow with `claude_state="waiting_input"` contains INDICATOR_WAITING_INPUT
- `test_session_row_claude_idle_shows_dim_indicator`: SessionRow with `claude_state="idle"` contains INDICATOR_WAITING

For the async `test_set_sessions_*` tests, update the `_make_session` / `_claude_session` helper calls and assertions as needed. The `_claude_session` helper should accept an optional `claude_state` parameter.
  </action>
  <verify>
    <automated>cd /Users/pieter/Github/joy && python -m pytest tests/test_terminal_pane.py tests/test_hooks.py tests/test_terminal_sessions.py -x -v 2>&1 | tail -40</automated>
  </verify>
  <done>
    - SessionRow renders 3 distinct claude states: green circle (busy), yellow circle (waiting_input), dim hollow circle (idle)
    - TerminalPane.set_sessions() prefers claude_state from hook, falls back to heuristic
    - Sort order: waiting_input sessions surface first (need attention)
    - Legend modal includes all 3 claude states
    - `joy setup-hooks` CLI command works
    - All existing and new tests pass
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Hook script stdin | JSON piped from Claude Code process to hook script |
| State files on disk | Written by hook script, read by joy in background thread |
| settings.json | Shared config file between joy and Claude Code |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-amk-01 | Tampering | ~/.joy/claude-states/*.json | accept | Low risk: local files, single-user machine. Joy wraps reads in try/except and falls back to heuristic on corrupt data. |
| T-amk-02 | Tampering | ~/.claude/settings.json | mitigate | setup_hooks() reads, validates JSON structure, and writes back. Backup not needed for personal tool but merge is non-destructive (append-only). |
| T-amk-03 | Denial of Service | Hook script performance | accept | Measured at 21ms per invocation. Even 20 PreToolUse events = 420ms spread across a turn. Negligible. |
| T-amk-04 | Information Disclosure | session_id in state files | accept | session_id is an opaque identifier, not sensitive. Files are in user-owned ~/.joy/ with default permissions. |
</threat_model>

<verification>
1. Run full test suite: `python -m pytest tests/ -x --timeout=30`
2. Manual: Start joy, verify Claude sessions show colored indicators
3. Manual: Run `joy setup-hooks`, verify ~/.joy/bin/claude-state-hook.sh exists and is executable
4. Manual: Verify ~/.claude/settings.json has all 6 hook events with joy's command alongside existing hooks
</verification>

<success_criteria>
- TerminalSession model has claude_state field
- Hook script installed at ~/.joy/bin/claude-state-hook.sh
- setup_hooks() merges into settings.json idempotently
- _read_claude_states() reads state files into dict
- fetch_sessions() populates claude_state (only when is_claude=True)
- TerminalPane shows 3 distinct indicators: green (busy), yellow (waiting_input), dim (idle)
- Sort order surfaces waiting_input sessions first
- Legend updated with all 3 states
- All tests pass (new + existing)
</success_criteria>

<output>
After completion, create `.planning/quick/260429-amk-implement-claude-agent-status-detection-/260429-amk-SUMMARY.md`
</output>
