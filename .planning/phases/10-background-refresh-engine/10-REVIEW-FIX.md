---
phase: 10-background-refresh-engine
fixed_at: 2026-04-13T13:55:00Z
review_path: .planning/phases/10-background-refresh-engine/10-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-04-13T13:55:00Z
**Source review:** .planning/phases/10-background-refresh-engine/10-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### WR-01: Class-level mutable default `_config` shared across JoyApp instances

**Files modified:** `src/joy/app.py`
**Commit:** 90fceed
**Applied fix:** Replaced class-level `_config: Config = Config()`, `_last_refresh_at`, `_refresh_failed`, and `_refresh_timer` declarations with instance attributes in a new `__init__` method, preventing state bleed between test runs and production re-instantiations.

---

### WR-02: `self._projects` used before assignment — AttributeError if action fires before load completes

**Files modified:** `src/joy/app.py`
**Commit:** 90fceed
**Applied fix:** Added `self._projects: list[Project] = []` in `__init__` alongside the other instance attribute initializations. This ensures `_projects` always exists as an instance attribute from construction time, even if `action_new_project` fires before `_load_data` completes.

---

### WR-03: Timer created with default `_config.refresh_interval` before user config loads

**Files modified:** `src/joy/app.py`
**Commit:** 90fceed
**Applied fix:** Removed the `set_interval` call from `on_mount`. Moved timer creation into `_set_projects`, after `self._config = config` is applied. Added a stop/reset guard so repeated `_set_projects` calls (e.g. in tests) cleanly replace the prior timer. The timer now starts with the user's configured interval.

---

### WR-04: `remove_children()` result not awaited — duplicated content on repeated calls

**Files modified:** `src/joy/widgets/worktree_pane.py`, `src/joy/app.py`, `tests/test_refresh.py`, `tests/test_worktree_pane.py`
**Commit:** a035fde
**Applied fix:** Made `set_worktrees` an `async` method and added `await` before `scroll.remove_children()`. Updated `_set_worktrees` in `app.py` to be `async` so it properly awaits the coroutine (Textual's `call_from_thread` handles async callables). Updated all direct callers in `test_refresh.py` (tests 4 and 5) and `test_worktree_pane.py` (5 call sites) to `await pane.set_worktrees(...)`. All 224 tests pass after the change.

---

### WR-05: First-boot refresh failure is silently dropped — stale icon never shown

**Files modified:** `src/joy/app.py`
**Commit:** 90fceed
**Applied fix:** Added a check inside the `if self._last_refresh_at is None` branch of `_update_refresh_label`: when `_refresh_failed` is True and no successful refresh has ever occurred, the method now calls `set_refresh_label("never", stale=True)` before returning. This surfaces the stale warning icon even on the very first failure, matching the behavior the reviewer expected.

---

_Fixed: 2026-04-13T13:55:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
