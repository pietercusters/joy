---
phase: 260416-of2-improve-iterm2-integration-link-projects
reviewed: 2026-04-16T00:00:00Z
depth: quick
files_reviewed: 11
files_reviewed_list:
  - src/joy/app.py
  - src/joy/models.py
  - src/joy/resolver.py
  - src/joy/store.py
  - src/joy/terminal_sessions.py
  - src/joy/widgets/terminal_pane.py
  - tests/test_models.py
  - tests/test_resolver.py
  - tests/test_store.py
  - tests/test_terminal_pane.py
  - tests/test_terminal_sessions.py
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 260416-of2: Code Review Report

**Reviewed:** 2026-04-16
**Depth:** quick (with focused reads on flagged areas)
**Files Reviewed:** 11
**Status:** issues_found

## Summary

The iTerm2 integration work is well-structured overall. The tab_id-based matching in the resolver and the `fetch_sessions` return-value upgrade to `(sessions, live_tab_ids)` are clean. Four issues were found that could cause silent data corruption, infinite auto-create loops, a data race, and a wrong-side-effect in the stale-heal logic. Two info items cover dead code and a minor defensive gap.

---

## Warnings

### WR-01: `_do_create_tab_for_project` mutates `project.iterm_tab_id` from a background thread

**File:** `src/joy/app.py:673`
**Issue:** The `@work(thread=True)` worker writes directly to `project.iterm_tab_id` on the `Project` object, which lives on the main thread. This is a data race: the main thread may simultaneously read `project.iterm_tab_id` in `_set_terminal_sessions` (e.g. during the next timer-triggered refresh that fires while the tab-creation worker is still running). The mutation happens before `call_from_thread` is used, so it is not serialised through the event loop.
**Fix:** Move the mutation to the main thread by passing `tab_id` back through `call_from_thread`:

```python
@work(thread=True, exit_on_error=False)
def _do_create_tab_for_project(self, project: Project) -> None:
    from joy.terminal_sessions import create_tab  # noqa: PLC0415
    tab_id = create_tab(project.name)
    if tab_id:
        self.app.call_from_thread(self._apply_tab_id, project, tab_id)

def _apply_tab_id(self, project: Project, tab_id: str) -> None:
    """Apply tab_id on the main thread (thread-safe)."""
    project.iterm_tab_id = tab_id
    self._save_projects_bg()
    self._load_terminal()
```

---

### WR-02: Stale-heal loop triggers `_do_create_tab_for_project` on every refresh cycle until the worker completes

**File:** `src/joy/app.py:252-254`
**Issue:** The stale-heal branch fires `_do_create_tab_for_project(project)` when `project.iterm_tab_id is None`. Because `_do_create_tab_for_project` is `@work(thread=True)` and writes `project.iterm_tab_id` from the worker thread (see WR-01), there is a window where the worker has not yet written back the result. During that window, every subsequent refresh cycle (timer fires every `refresh_interval` seconds) will see `iterm_tab_id is None` and spawn another tab-creation worker. Each worker calls `create_tab`, opening a new iTerm2 tab. Multiple simultaneous workers on the same project will all succeed and write different `tab_id` values — the last one to call `call_from_thread` wins, leaving orphaned tabs and only one stored tab_id.

Even if WR-01 is fixed (write via `call_from_thread`), the race window between "worker started" and "tab_id applied on main thread" still spans multiple refresh ticks. A guard is needed.

**Fix:** Track in-flight tab creation to prevent duplicate workers:

```python
# In __init__:
self._tab_creating: set[str] = set()  # project names with in-flight tab creation

# In _set_terminal_sessions stale-heal branch:
elif project.iterm_tab_id is None and project.name not in self._tab_creating:
    self._tab_creating.add(project.name)
    self._do_create_tab_for_project(project)

# In _apply_tab_id (main-thread callback from WR-01 fix):
def _apply_tab_id(self, project: Project, tab_id: str) -> None:
    self._tab_creating.discard(project.name)
    project.iterm_tab_id = tab_id
    self._save_projects_bg()
    self._load_terminal()

# Also discard on failure (add a failure callback or always discard in worker):
@work(thread=True, exit_on_error=False)
def _do_create_tab_for_project(self, project: Project) -> None:
    from joy.terminal_sessions import create_tab  # noqa: PLC0415
    tab_id = create_tab(project.name)
    if tab_id:
        self.app.call_from_thread(self._apply_tab_id, project, tab_id)
    else:
        self.app.call_from_thread(self._tab_creating.discard, project.name)
```

---

### WR-03: `_do_activate_tab` reads `self._current_sessions` from a background thread

**File:** `src/joy/app.py:681`
**Issue:** `_do_activate_tab` is `@work(thread=True)` and iterates `self._current_sessions` (line 681) without any synchronization. `_current_sessions` is replaced wholesale in `_set_terminal_sessions` on the main thread (`self._current_sessions = sessions or []`). In CPython the GIL makes list-replacement atomic at the bytecode level, but iterating the list while it is being replaced on another thread is not safe: the iterator holds a reference to the old list object, so replacement is benign in practice, but this is an implementation detail of CPython, not a language guarantee. More concretely, if `_current_sessions` is replaced between the `for` binding and the first `session.tab_id` access, the loop runs on a now-stale snapshot — the correct tab may not be found even though it exists in the new list.

The safer pattern is to snapshot the list on the main thread before dispatching the worker:

**Fix:**
```python
def action_open_terminal(self) -> None:
    ...
    if project.iterm_tab_id:
        # Snapshot sessions on main thread before handing to worker
        sessions_snapshot = list(self._current_sessions)
        self._do_activate_tab(project.iterm_tab_id, sessions_snapshot)

@work(thread=True, exit_on_error=False)
def _do_activate_tab(self, tab_id: str, sessions: list) -> None:
    from joy.terminal_sessions import activate_session  # noqa: PLC0415
    for session in sessions:
        if session.tab_id == tab_id:
            activate_session(session.session_id)
            return
    self.app.call_from_thread(self.notify, "Tab session not found", severity="warning", markup=False)
```

---

### WR-04: `_load_terminal` tuple unpacking silently discards `live_tab_ids` when `fetch_sessions` returns `None`

**File:** `src/joy/app.py:198-201`
**Issue:** The unpacking logic is correct — the `if result is not None` branch unpacks properly. However, the `else` branch sets `live_tab_ids = set()` and then `_set_terminal_sessions(None, set())` is called via `call_from_thread`. Inside `_set_terminal_sessions`, the stale-heal `if sessions is not None:` guard correctly skips the heal loop when `sessions is None`. This is fine.

The actual issue is subtler: when `fetch_sessions()` returns `None` (iTerm2 unavailable), `_mark_terminal_refresh_success()` is still called on line 203:

```python
self.app.call_from_thread(self._mark_terminal_refresh_success)  # line 203
```

This records a successful refresh timestamp and clears `_terminal_refresh_failed`, even though the fetch returned `None` (failure). The border label will show a fresh timestamp instead of "never / stale". The `TerminalPane` correctly shows "iTerm2 unavailable", but the border title misleadingly shows "Terminal  just now".

**Fix:** Only call `_mark_terminal_refresh_success` when `result is not None`:

```python
result = fetch_sessions()
if result is not None:
    sessions, live_tab_ids = result
    self.app.call_from_thread(self._set_terminal_sessions, sessions, live_tab_ids)
    self.app.call_from_thread(self._mark_terminal_refresh_success)
else:
    self.app.call_from_thread(self._set_terminal_sessions, None, set())
    self.app.call_from_thread(self._mark_terminal_refresh_failure)
```

---

## Info

### IN-01: `tab_groups` list comprehension includes stale `iterm_tab_id` values during the stale-heal cycle

**File:** `src/joy/app.py:259-263`
**Issue:** The `tab_groups` comprehension (built after the stale-heal loop) correctly filters to only `p.iterm_tab_id in live_tab_ids`. This means cleared-but-not-yet-saved entries (where `project.iterm_tab_id` was just set to `None`) are excluded. Newly-created tabs (written by the background worker after this point) are also excluded from this cycle's render. Both cases are handled correctly by the filter. No bug — this is already right. Noting it explicitly since it was called out as a focus area: the comprehension is correct.

### IN-02: `create_session` in `terminal_sessions.py` is now unreachable dead code

**File:** `src/joy/terminal_sessions.py:109-137`
**Issue:** `create_session` (returns `session_id`) is superseded by `create_tab` (returns `tab_id`). The only caller in `terminal_pane.py` (`_do_create_session` at line 430) still calls `create_session`, not `create_tab`. If the intent is for the "n: New" session binding in `TerminalPane` to create a tab-linked session, the caller should use `create_tab`. If `create_session` is intentionally kept as a session-only (not tab-linked) path, it should be documented. As written, `action_new_session` creates a session without storing a `tab_id`, so the new session will appear under "Other" rather than under a project group — which may or may not be intentional.

---

_Reviewed: 2026-04-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick (with targeted file reads on flagged areas)_
