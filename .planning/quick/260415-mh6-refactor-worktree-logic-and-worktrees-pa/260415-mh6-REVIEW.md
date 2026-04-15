---
phase: 260415-mh6
reviewed: 2026-04-15T00:00:00Z
depth: quick
files_reviewed: 3
files_reviewed_list:
  - src/joy/app.py
  - src/joy/widgets/worktree_pane.py
  - tests/test_worktree_pane_cursor.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 260415-mh6: Code Review Report

**Reviewed:** 2026-04-15T00:00:00Z
**Depth:** quick (standard file read applied — small file set)
**Files Reviewed:** 3
**Status:** issues_found

## Summary

The refactor is clean and well-reasoned. The delegation chain (`action_activate_row` -> `app.action_open_ide` -> `_open_worktree_path`) is correct and the `@work(thread=True)` decorator is applied to the right layer. Two warnings and two info items found; no critical issues.

## Warnings

### WR-01: `self.notify()` called from inside a `@work(thread=True)` worker

**File:** `src/joy/app.py:733`, `src/joy/app.py:739`
**Issue:** `_open_worktree_path` is decorated with `@work(thread=True, exit_on_error=False)`. Inside the worker body, `self.notify(...)` is called directly on two paths (path-not-found and exception handler). Textual's `notify()` posts a message and updates the DOM, which must happen on the main thread. Calling it from a worker thread is a thread-safety violation; in practice it often works because Textual queues messages internally, but it is undocumented, races against the event loop, and may produce silent failures or visual glitches in future Textual versions.

**Fix:** Use `self.app.call_from_thread(self.notify, ...)` for all notify calls inside the worker:
```python
@work(thread=True, exit_on_error=False)
def _open_worktree_path(self, path: str) -> None:
    from pathlib import Path as _Path
    if not _Path(path).exists():
        self.call_from_thread(
            self.notify,
            f"Worktree path not found: {path}",
            severity="warning",
            markup=False,
        )
        return
    ide = self._config.ide or "Cursor"
    try:
        _subprocess.run(["open", "-a", ide, path], check=False)
    except Exception as exc:
        self.call_from_thread(
            self.notify,
            f"Failed to open IDE: {exc}",
            severity="error",
            markup=False,
        )
```

### WR-02: `action_open_ide` accesses private widget state (`pane._cursor`, `pane._rows`) across the widget boundary

**File:** `src/joy/app.py:722-725`
**Issue:** `action_open_ide` directly reads `pane._cursor` and `pane._rows`. These are private to `WorktreePane`. If either attribute is absent (e.g., `WorktreePane.__init__` is changed) the access raises `AttributeError` with no guard. More importantly, `action_open_ide` already has a guard `if pane._cursor < 0 or not pane._rows`, but `pane._cursor >= len(pane._rows)` is not checked — if `_cursor` is somehow out-of-range (e.g., during a DOM rebuild triggered by a rapid refresh), `pane._rows[pane._cursor]` will raise `IndexError`.

**Fix:** Add a bounds check before the index access, or expose a `highlighted_path() -> str | None` method on `WorktreePane` to encapsulate the lookup:
```python
# Option A: add bounds check in app.py
if pane._cursor < 0 or pane._cursor >= len(pane._rows):
    self.notify("No worktree selected", markup=False)
    return
self._open_worktree_path(pane._rows[pane._cursor].path)

# Option B (preferred): add to WorktreePane
def highlighted_path(self) -> str | None:
    if 0 <= self._cursor < len(self._rows):
        return self._rows[self._cursor].path
    return None
```

## Info

### IN-01: Duplicate `_cursor` guard — `action_activate_row` and `action_open_ide` both guard independently

**File:** `src/joy/widgets/worktree_pane.py:456-458`
**Issue:** `action_activate_row` guards with `if self._cursor < 0 or self._cursor >= len(self._rows): return` before calling `self.app.action_open_ide()`, which itself re-checks `pane._cursor < 0 or not pane._rows`. The double guard is harmless but signals that the two entry points are loosely coupled: if the guard logic diverges in the future, one path could bypass the other's check. The `not pane._rows` check in `action_open_ide` is also slightly inconsistent with the `>= len(self._rows)` check in `action_activate_row` (functionally equivalent but expressed differently).

**Fix:** Consider removing the guard from `action_activate_row` entirely (trusting `action_open_ide` to guard), or standardise on one guard expression:
```python
def action_activate_row(self) -> None:
    """Open the highlighted worktree in the IDE (Enter key — delegates to app)."""
    self.app.action_open_ide()
```

### IN-02: Test `Config` construction without required `ide` key — coupling to model defaults

**File:** `tests/test_worktree_pane_cursor.py:150`, `tests/test_worktree_pane_cursor.py:183`
**Issue:** Tests assign `app._config = Config(ide="Cursor")` and `Config(ide="PyCharm")`, but `_config` is already set in `JoyApp.__init__`. The test `_TestApp` does not extend `JoyApp`, so this works by direct attribute injection on a plain `App` subclass, but `_config` is never declared on the test class — it relies on Python's dynamic attribute assignment. If `action_open_ide` is ever refactored to access `self._config` via a property or type-checked accessor, these tests will silently break or hit an `AttributeError` rather than a clear test failure. Additionally, `Config(ide="Cursor")` is injected but `action_open_ide` is fully mocked (`ide_calls.append`), so the `_config` injection has no effect in these tests and is dead setup code.

**Fix:** Remove the unused `app._config = Config(...)` lines from `test_enter_always_opens_ide_even_with_mr` and `test_enter_opens_ide_when_no_mr`, since `action_open_ide` is overridden and never reads `_config`:
```python
# Remove these two lines — they have no effect
# app._config = Config(ide="Cursor")
```

---

_Reviewed: 2026-04-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick (files read for correctness — 3 files, ~650 lines total)_
