---
phase: 12-iterm2-integration-terminal-pane
plan: "01"
subsystem: terminal-sessions-data-layer
tags: [iterm2, dataclass, fetch, activate, tdd]
dependency_graph:
  requires: []
  provides: [TerminalSession-dataclass, fetch_sessions, activate_session, _SHELL_PROCESSES]
  affects: [12-02-terminal-pane-ui, 12-03-app-wiring]
tech_stack:
  added: [iterm2>=2.15]
  patterns: [lazy-import-in-worker, Connection-instance-method, catch-all-exception-return-none]
key_files:
  created:
    - src/joy/terminal_sessions.py
    - tests/test_terminal_sessions.py
  modified:
    - src/joy/models.py
    - pyproject.toml
decisions:
  - "Use Connection().run_until_complete() (instance method) exclusively -- avoids sys.exit(1) trap in module-level iterm2.run_until_complete()"
  - "All iterm2 imports are lazy (inside function bodies) to preserve TUI startup time"
  - "Catch all exceptions in both fetch_sessions and activate_session -- never raise, always return None/False"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-13T16:51:15Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 12 Plan 01: Terminal Sessions Data Layer Summary

**One-liner:** iTerm2 session data layer using Connection().run_until_complete() with TerminalSession dataclass, lazy imports, and full exception safety.

## What Was Built

### TerminalSession Dataclass (models.py)

Added `TerminalSession` dataclass after `MRInfo` in `src/joy/models.py`:
- `session_id: str` — globally unique iTerm2 session ID
- `session_name: str` — session display name
- `foreground_process: str` — name of foreground process (e.g. "claude", "zsh")
- `cwd: str` — current working directory
- No `to_dict()` method (computed data, never persisted to TOML — same pattern as WorktreeInfo/MRInfo)

### iterm2 Dependency (pyproject.toml)

Added `"iterm2>=2.15"` as the third required dependency alongside tomli-w and textual.

### terminal_sessions.py Module

New module at `src/joy/terminal_sessions.py` with:

**`fetch_sessions() -> list[TerminalSession] | None`**
- Uses `Connection().run_until_complete(_enumerate, retry=False)` — the instance method, NOT the module-level `iterm2.run_until_complete()` (which calls sys.exit(1) on ConnectionRefusedError)
- Traverses `app.terminal_windows -> window.tabs -> tab.sessions`
- Reads `jobName` and `path` variables via `session.async_get_variable()` with `or ""` default
- Accesses `session.name` as plain attribute (NOT awaited)
- Returns `None` on any exception — never raises

**`activate_session(session_id: str) -> bool`**
- Uses same `Connection().run_until_complete()` pattern
- Calls `session.async_activate(select_tab=True, order_window_front=True)` then `app.async_activate()`
- Returns `True` on success, `False` if session not found or any exception

**`_SHELL_PROCESSES: frozenset`**
- Contains `{"zsh", "bash", "fish"}` — exported for Plan 02 Claude detection logic

### Test Suite (tests/test_terminal_sessions.py)

11 tests covering:
- `fetch_sessions` returns list when API reachable (mocked Connection)
- `fetch_sessions` returns None on `ConnectionRefusedError`
- `fetch_sessions` returns None on any other exception
- `fetch_sessions` defaults None variables to empty string
- `activate_session` returns True when session found and activated
- `activate_session` returns False when get_session_by_id returns None
- `activate_session` returns False when Connection raises exception
- `_SHELL_PROCESSES` contains "zsh", "bash", "fish" and is a frozenset

## Commits

| Task | Type | Commit | Description |
|------|------|--------|-------------|
| 1 | feat | 3388239 | TerminalSession dataclass + iterm2 dependency |
| 2 (RED) | test | 4ce1e8c | Failing tests for terminal_sessions module |
| 2 (GREEN) | feat | 6b2b748 | Implement terminal_sessions with fetch/activate |

## Verification Results

```
uv run pytest tests/test_terminal_sessions.py -v
11 passed, 1 warning in 0.19s

uv run pytest tests/test_models.py tests/test_terminal_sessions.py tests/test_store.py tests/test_worktrees.py tests/test_mr_status.py -v
144 passed, 1 warning in 2.05s

uv run python -c "from joy.models import TerminalSession; print(list(TerminalSession.__dataclass_fields__.keys()))"
['session_id', 'session_name', 'foreground_process', 'cwd']
```

## Deviations from Plan

None - plan executed exactly as written.

## Threat Model Compliance

| Threat | Mitigation Applied |
|--------|-------------------|
| T-12-01 (DoS via exception) | Catch-all exception in fetch_sessions returns None; never crashes TUI |
| T-12-03 (sys.exit via module-level run_until_complete) | Used Connection() instance method exclusively throughout |

## Known Stubs

None. All functions are fully implemented and return real data or None (not placeholder/hardcoded values).

## Self-Check: PASSED

- [x] `src/joy/terminal_sessions.py` exists
- [x] `tests/test_terminal_sessions.py` exists
- [x] `src/joy/models.py` contains TerminalSession dataclass
- [x] `pyproject.toml` contains `iterm2>=2.15`
- [x] Commit 3388239 exists
- [x] Commit 4ce1e8c exists
- [x] Commit 6b2b748 exists
- [x] All 11 tests pass
