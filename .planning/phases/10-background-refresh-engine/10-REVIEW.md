---
phase: 10-background-refresh-engine
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - tests/test_refresh.py
  - src/joy/widgets/worktree_pane.py
  - src/joy/app.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files were reviewed: the new background-refresh test suite, the WorktreePane widget, and the main JoyApp entry point. The implementation is well-structured and the feature contract is clearly expressed through tests. However, there are five warning-level issues that could cause bugs in production or under test: a classic Python class-variable mutation footgun in `JoyApp`, a missing `AttributeError` path before async data loads complete, a likely silent failure path when the very first worktree refresh fails, an unwaited `remove_children()` call in `set_worktrees` that risks rendering duplicated content on repeated refreshes, and a timer-interval race where the user's configured interval is never actually used. Three info-level items round out the review.

---

## Warnings

### WR-01: Class-level mutable default `_config` shared across JoyApp instances

**File:** `src/joy/app.py:58`
**Issue:** `_config`, `_last_refresh_at`, `_refresh_failed`, and `_refresh_timer` are declared as class attributes. In Python, a class-level `_config: Config = Config()` evaluates `Config()` once at class-definition time. Every `JoyApp()` instance shares that same object until the instance attribute is re-assigned. In tests, two separate `JoyApp()` instances (across test functions) see the same `_config` object, which can bleed state between tests. In production this only matters if `JoyApp` is instantiated more than once, but it is a latent footgun that makes the test isolation fragile.

**Fix:**
```python
# Move all mutable state into __init__ (or on_mount):
def __init__(self, **kwargs) -> None:
    super().__init__(**kwargs)
    self._config: Config = Config()
    self._last_refresh_at: datetime | None = None
    self._refresh_failed: bool = False
    self._refresh_timer: object | None = None
```

---

### WR-02: `self._projects` used before assignment — AttributeError if action fires before load completes

**File:** `src/joy/app.py:229`
**Issue:** `action_new_project` reads `self._projects` (line 229) before it is ever set as an instance attribute. `_projects` is first assigned inside `_set_projects`, which runs as a callback from the `_load_data` background worker. If a user presses `n` before `_load_data` completes (very fast keystroke on slow startup, or in automated tests with short pauses), `self._projects` does not exist and raises `AttributeError`. There is no class-level `_projects = []` fallback.

**Fix:**
```python
# Add to __init__ (or alongside the other class attributes if staying class-level):
self._projects: list[Project] = []
```
Or guard defensively in `action_new_project`:
```python
projects = getattr(self, "_projects", [])
if any(p.name == name for p in projects):
    ...
```

---

### WR-03: Timer created with default `_config.refresh_interval` before user config loads

**File:** `src/joy/app.py:77-79`
**Issue:** `on_mount` creates the periodic timer immediately using `self._config.refresh_interval`. At this point `_config` is still the default `Config()` instance (class-level default), because `_load_data` is a background worker that hasn't returned yet. The user's configured `refresh_interval` is loaded in `_set_projects` (line 93-94) and stored to `self._config`, but the timer is already set with the old value. The timer interval is therefore always the default, never the user's configured value.

**Fix:** Create the timer after config is loaded, inside `_set_projects`:
```python
def _set_projects(self, projects: list[Project], config: Config | None = None) -> None:
    self._projects = projects
    if config is not None:
        self._config = config
        # Reset timer with the user's interval now that config is available
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        self._refresh_timer = self.set_interval(
            self._config.refresh_interval, self._trigger_worktree_refresh
        )
    ...
```

---

### WR-04: `remove_children()` result not awaited in `set_worktrees` — duplicated content on repeated calls

**File:** `src/joy/widgets/worktree_pane.py:223`
**Issue:** `scroll.remove_children()` in Textual returns an `AwaitComplete` (an awaitable). Calling it without `await` schedules the removal but does not wait for it to complete before `scroll.mount(...)` is called. On the first call this may work by accident (nothing to remove), but on subsequent calls the old children are still in the DOM when new ones are mounted, producing duplicated rows. This directly undermines the "Idempotent (D-03)" requirement and the scroll-preservation tests assume clean rebuilds.

Because `set_worktrees` is a synchronous method called from the main thread, the fix is to make it a coroutine or use `call_after_refresh`:
```python
# Option A: make set_worktrees async (requires callers to await it or use call_later):
async def set_worktrees(self, worktrees: list[WorktreeInfo], ...) -> None:
    scroll = self.query_one("#worktree-scroll", _WorktreeScroll)
    saved_scroll_y = scroll.scroll_y
    await scroll.remove_children()
    ...

# Option B: stay synchronous but use remove_children().wait() if available,
# or restructure to replace content via a single container swap.
```
Check the Textual 8.x API for `remove_children()` return type and whether `await` is valid in the calling context.

---

### WR-05: First-boot refresh failure is silently dropped — stale icon never shown

**File:** `src/joy/app.py:136-150`
**Issue:** When the very first `_load_worktrees` call raises an exception, `_mark_refresh_failure` sets `_refresh_failed = True` then calls `_update_refresh_label`. `_update_refresh_label` returns early if `_last_refresh_at is None` (line 143), so no stale icon is pushed to the pane. The user sees the "Loading…" placeholder with no indication that the refresh failed. The `test_refresh_failure_shows_stale` test avoids this path by doing a successful refresh first, so this edge case is untested.

**Fix:** Handle the case where failure occurs before any success:
```python
def _update_refresh_label(self) -> None:
    if self._last_refresh_at is None:
        if self._refresh_failed:
            # No successful refresh yet, but one has failed — show stale
            self.query_one(WorktreePane).set_refresh_label("never", stale=True)
        return
    ...
```

---

## Info

### IN-01: Wave 1 tests mix `asyncio.run()` with pytest — potential event-loop conflict

**File:** `tests/test_refresh.py:130,151,174,212,245`
**Issue:** The five Wave 1 tests define an inner `async def _run()` and call `asyncio.run(_run())` inside a synchronous `def test_*` function. The Wave 2 tests use `@pytest.mark.asyncio` consistently. If `pytest-asyncio` is configured with `asyncio_mode = "auto"`, or if another test in the suite installs a custom event loop policy, calling `asyncio.run()` inside a sync test can conflict. The inconsistency also makes the test style harder to follow.

**Fix:** Convert Wave 1 tests to the same pattern as Wave 2:
```python
@pytest.mark.asyncio
async def test_set_refresh_label_normal():
    app = _TestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(WorktreePane)
        pane.set_refresh_label("2m ago", stale=False)
        assert pane.border_title == "Worktrees  2m ago"
```

---

### IN-02: `test_scroll_preserved_across_set_worktrees` has a timing assumption that may be fragile on slow CI

**File:** `tests/test_refresh.py:204-211`
**Issue:** After the second `set_worktrees`, the test waits `await pilot.pause(0.1)` before asserting `scroll.scroll_y == saved_y`. The scroll restoration is scheduled via `call_after_refresh`, which fires after the next Textual render cycle — not after 0.1 s of wall-clock time. On an underpowered CI runner, if rendering is slow, the assertion may fire before the lambda runs. Related to WR-04: if `remove_children()` is not awaited, the scroll position may also be undefined.

**Fix:** After `set_worktrees`, advance the Textual event loop explicitly rather than relying on wall-clock time:
```python
pane.set_worktrees(worktrees)
await pilot.pause()      # let Textual process pending events
await app.workers.wait_for_complete()
```
Or expose `set_worktrees` as async so callers can `await` completion.

---

### IN-03: Magic constant `2 *` in stale-detection threshold is inline with no named constant

**File:** `src/joy/app.py:149`
**Issue:** The stale detection formula `age_seconds > (2 * self._config.refresh_interval)` uses the inline multiplier `2` with no explanation of why two intervals constitutes staleness. If this policy needs tuning it requires finding this magic number in context.

**Fix:** Extract to a named constant at module level or document inline:
```python
_STALE_MULTIPLIER = 2  # data is stale after 2x the refresh interval

stale = self._refresh_failed or age_seconds > (_STALE_MULTIPLIER * self._config.refresh_interval)
```

---

_Reviewed: 2026-04-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
