---
plan: 17-03
phase: 17-fix-iterm2-integration-bugs
status: complete
completed: 2026-04-16
requirements:
  - FIX17-CLOSE-TAB
---

## Summary

Fixed UAT gap: newly created iTerm2 tab is now focused immediately after h-key creation.

## What was built

Added two lines to `create_tab` in `src/joy/terminal_sessions.py`:
- `await tab.async_select()` — selects the new tab in the iTerm2 window
- `await app.async_activate()` — brings iTerm2 to the foreground

This mirrors the existing `activate_session` focus pattern. The fix runs inside the `_create` coroutine after `result = tab.tab_id` is set, so the return value is unchanged.

Updated `test_create_tab_returns_tab_id` in `tests/test_terminal_sessions.py` to:
- Add `AsyncMock` for `mock_tab.async_select`
- Add `AsyncMock` for `mock_app.async_activate`
- Assert both are called once

## Key files

- `src/joy/terminal_sessions.py` — `create_tab` function, lines 151–164
- `tests/test_terminal_sessions.py` — `TestCreateTab.test_create_tab_returns_tab_id`

## Verification

- `uv run pytest tests/test_terminal_sessions.py -q` — 22 passed, 0 failures
- `grep "await tab.async_select()" src/joy/terminal_sessions.py` — match at line 163
- `grep "await app.async_activate()" src/joy/terminal_sessions.py` — matches in both `create_tab` (line 164) and `activate_session` (line 277)

## Self-Check: PASSED

All acceptance criteria met:
- [x] `await tab.async_select()` exists inside `create_tab`
- [x] `await app.async_activate()` exists inside `create_tab`
- [x] Test asserts both focus calls
- [x] All 22 tests pass
- [x] `create_tab` still returns `tab_id` on success, `None` on failure
