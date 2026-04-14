---
phase: 12-iterm2-integration-terminal-pane
reviewed: 2026-04-14T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - pyproject.toml
  - src/joy/app.py
  - src/joy/models.py
  - src/joy/terminal_sessions.py
  - src/joy/widgets/terminal_pane.py
  - tests/test_models.py
  - tests/test_pane_layout.py
  - tests/test_refresh.py
  - tests/test_terminal_pane.py
  - tests/test_terminal_sessions.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-04-14
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 12 adds an iTerm2 terminal session integration: a pure-data fetch layer (`terminal_sessions.py`), a Textual widget (`terminal_pane.py`), and app wiring (`_load_terminal` worker in `app.py`). The overall architecture is sound — lazy iTerm2 imports, background worker thread, independent failure path from worktrees, and multi-signal Claude detection. Tests are comprehensive and well-structured.

Two warnings are worth fixing: one is a logic gap in the error-tracking path that makes terminal failure detection unreachable in practice, and one is an internal coupling between the UI widget and a data-layer constant. Three informational items cover a discarded return value, an install-time dependency concern, and a minor test fragility.

## Warnings

### WR-01: Terminal refresh failure path is unreachable — `_mark_terminal_refresh_failure` never fires

**File:** `src/joy/app.py:141-152`

**Issue:** `_load_terminal` wraps `fetch_sessions()` in a try/except and calls `_mark_terminal_refresh_failure` in the except branch. However, `fetch_sessions()` already catches every exception internally and returns `None` rather than raising. The outer except in `_load_terminal` can therefore never be triggered by any normal iTerm2 failure (unavailable, refused connection, API error). This means `_terminal_refresh_failed` is always `False`, and the stale warning on the TerminalPane border title is never shown — even when iTerm2 is genuinely unavailable.

The correct detection point is the `None` return value from `fetch_sessions()`, not an exception from it.

**Fix:**
```python
@work(thread=True, exit_on_error=False)
def _load_terminal(self) -> None:
    """Load terminal session data in background thread (D-15)."""
    from joy.terminal_sessions import fetch_sessions  # noqa: PLC0415

    try:
        sessions = fetch_sessions()
        self.app.call_from_thread(self._set_terminal_sessions, sessions)
        if sessions is None:
            self.app.call_from_thread(self._mark_terminal_refresh_failure)
        else:
            self.app.call_from_thread(self._mark_terminal_refresh_success)
    except Exception:
        self.app.call_from_thread(self._set_terminal_sessions, None)
        self.app.call_from_thread(self._mark_terminal_refresh_failure)
```

The `test_terminal_unavailable_shows_message` and `test_terminal_refresh_independent` tests in `tests/test_refresh.py` patch `fetch_sessions` to return `None` (not raise), which confirms this is the real failure path. The test `test_terminal_refresh_label_updates` only checks that a timestamp appears on success — there is no test asserting that `_terminal_refresh_failed` is set to `True` when `fetch_sessions` returns `None`, which is why this bug is currently undetected.

---

### WR-02: `set_sessions` imports a private constant from `terminal_sessions` — tight coupling between UI and data layer

**File:** `src/joy/widgets/terminal_pane.py:231`

**Issue:** `set_sessions` does a lazy import of `_SHELL_PROCESSES` from `joy.terminal_sessions` to determine the busy/waiting state of Claude sessions. This imports a private implementation detail (`_SHELL_PROCESSES`, prefixed with underscore) from the data layer into the UI widget. Two problems:
1. The widget now silently depends on `terminal_sessions` being importable at render time — if `terminal_sessions` ever fails to import (e.g., missing `iterm2` at install), the widget crashes when `sessions` is non-empty.
2. The `is_busy` determination logic is duplicated: `fetch_sessions` already computes whether Claude is busy/idle (via `_detect_claude`), but the display-level busy/waiting distinction is re-derived from `foreground_process` in the widget. The `TerminalSession` model could carry an `is_busy: bool` field set at fetch time, removing the need for the widget to know about shell processes at all.

**Fix (minimal):** Move `_SHELL_PROCESSES` import to the module top level in `terminal_pane.py` so the coupling is explicit, not hidden inside a method:
```python
# At module level in terminal_pane.py
from joy.terminal_sessions import _SHELL_PROCESSES
```

**Fix (preferred):** Add `is_busy: bool = False` to `TerminalSession` in `models.py` and populate it in `fetch_sessions()`:
```python
# In models.py
@dataclass
class TerminalSession:
    session_id: str
    session_name: str
    foreground_process: str
    cwd: str
    is_claude: bool = False
    is_busy: bool = False   # True when Claude is the foreground process
```
Then in `terminal_pane.py`, replace the `_SHELL_PROCESSES` import and `is_busy` computation with `session.is_busy`.

---

## Info

### IN-01: `activate_session` return value silently discarded — no user feedback on activation failure

**File:** `src/joy/widgets/terminal_pane.py:301-305`

**Issue:** `_do_activate` calls `_ts.activate_session(session_id)` but discards the `bool` return value. When activation fails (session no longer exists, iTerm2 quit), the user gets no feedback — the Enter key press appears to do nothing.

**Fix:** Show a notification on failure:
```python
@work(thread=True, exit_on_error=False)
def _do_activate(self, session_id: str) -> None:
    import joy.terminal_sessions as _ts  # noqa: PLC0415
    success = _ts.activate_session(session_id)
    if not success:
        self.app.call_from_thread(
            self.app.notify, "Session no longer available", severity="warning", markup=False
        )
```

---

### IN-02: `iterm2` is a hard install-time dependency — blocks non-macOS installs and CI

**File:** `pyproject.toml:12`

**Issue:** `iterm2>=2.15` is listed as a hard dependency in `[project.dependencies]`. While all iterm2 imports in source code are correctly lazy (inside function bodies), the package is still required at `uv tool install` / `pip install` time. This means the package cannot be installed on Linux CI runners or any non-macOS machine, which limits testing options and contradicts the project goal of graceful degradation (iTerm2 should degrade to "unavailable", not fail to install).

**Fix option A (optional dependency):**
```toml
[project.optional-dependencies]
iterm2 = ["iterm2>=2.15"]
```

**Fix option B (soft dependency with try/except at import):** Keep it hard for now since joy is documented as macOS-only, but note this as a known CI limitation in CLAUDE.md. The current CI setup (pytest with mocked iterm2) handles it via `uv` resolving the package; this is only a concern if the test environment ever loses the `iterm2` package.

This is informational — the current setup works in practice since macOS is the only supported platform.

---

### IN-03: `_other_session` test factory omits explicit `is_claude=False` — silent reliance on dataclass default

**File:** `tests/test_terminal_pane.py:58-68`

**Issue:** `_other_session()` delegates to `_make_session()`, which constructs a `TerminalSession` without setting `is_claude`. The test relies on the dataclass default (`is_claude=False`). If `TerminalSession.is_claude` default ever changed, all tests using `_other_session()` would silently mis-classify sessions as Claude sessions, producing false-positive test passes (the grouping logic in `set_sessions` would put them in the Claude group while tests check for the Other group).

**Fix:** Pass `is_claude=False` explicitly in `_make_session` or `_other_session`:
```python
def _other_session(...) -> TerminalSession:
    return TerminalSession(
        session_id=session_id,
        session_name=session_name,
        foreground_process=foreground_process,
        cwd="/Users/pieter/Github/joy",
        is_claude=False,  # explicit: this is an "Other" session
    )
```

---

_Reviewed: 2026-04-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
