---
phase: 260415-qqx-build-full-iterm2-terminal-session-contr
reviewed: 2026-04-15T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - src/joy/app.py
  - src/joy/models.py
  - src/joy/operations.py
  - src/joy/resolver.py
  - src/joy/screens/confirmation.py
  - src/joy/store.py
  - src/joy/terminal_sessions.py
  - src/joy/widgets/object_row.py
  - src/joy/widgets/project_detail.py
  - src/joy/widgets/terminal_pane.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Code Review: iTerm2 Terminal Session Management

**Reviewed:** 2026-04-15
**Depth:** standard (thorough)
**Files Reviewed:** 10
**Status:** issues_found

## Summary

The new iTerm2 integration replaces all AppleScript subprocess calls with the Python `iterm2` API. The
`Connection().run_until_complete()` pattern is used consistently across all five new/updated functions
(`fetch_sessions`, `create_session`, `rename_session`, `close_session`, `activate_session`, `_open_iterm`).
This is architecturally sound and completely eliminates the previous AppleScript injection surface.

The `@work(thread=True)` usage is consistent and correct. Thread-to-UI transitions use
`call_from_thread` throughout. No data races were detected in the new code.

Five warnings and four info items were found. The most important is a logic bug in
`_propagate_terminal_auto_remove` that can delete all linked terminal objects the first time
the app starts before iTerm2 is fully connected. A secondary concern is a stale session_id
used in close/force-close after a rename.

---

## Warnings

### WR-01: Auto-remove fires on iTerm2 unavailable (None), not just on empty list

**File:** `src/joy/app.py:308-309`

**Issue:** The guard `if not self._current_sessions: return` treats both `None` (iTerm2
unreachable) and `[]` (genuinely no sessions open) identically — it skips removal in both
cases. However, `_set_terminal_sessions` converts `None` to `[]` before storing
(`self._current_sessions = sessions or []`). This means that if iTerm2 is unavailable,
`_current_sessions` is `[]`, the guard fires, and removal is correctly skipped.

BUT there is a subtler problem: the guard also skips removal when iTerm2 returns a genuinely
empty session list (e.g., user closed all tabs). In that case linked terminal objects are
never auto-removed even though the sessions are gone. This may be intentional (the comment
says "iTerm2 hiccup"), but it means the auto-remove can only fire when at least one session
exists. If the user closes all tabs except the ones linked to joy projects, those project
objects will never be cleaned up automatically.

More critically: on cold start, `_set_terminal_sessions` is called before `_set_worktrees`
completes. At that point `_current_sessions` may be an accurate non-empty list, so the guard
passes. If timing causes `_maybe_compute_relationships` to run before `_rel_index` is
populated (first cycle), `_propagate_terminal_auto_remove` will compare against whatever
sessions happened to load, and could remove still-valid objects. The two-flag
(`_worktrees_ready` + `_sessions_ready`) coordination prevents this for the resolver itself,
but `_propagate_changes` runs inside `_maybe_compute_relationships` which only fires when
both flags are set — so this is actually safe. No bug here, but worth a comment.

**The real bug:** `_current_sessions = sessions or []` flattens `None` to `[]`. The comment
at `app.py:229` says `(treat None as empty — pitfall 2 avoidance)`, but this means the
`if not self._current_sessions` guard in `_propagate_terminal_auto_remove` cannot distinguish
"iTerm2 down" from "no sessions open". If iTerm2 is briefly unavailable during a refresh
cycle, `_current_sessions` stays as the previous non-empty value (from the last good fetch)
because `_set_terminal_sessions(None)` will set it to `[]`. On the next good fetch, the
sessions list is repopulated. So the net effect is: one bad refresh produces `[]`, which
blocks auto-remove for that cycle — which is the intended safety behaviour. This is correct
but fragile and undocumented.

**Fix:** Add an explicit `None` sentinel to distinguish "iTerm2 unreachable" from "no
sessions". Store `_current_sessions: list[TerminalSession] | None = None` and guard on
`self._current_sessions is None`.

```python
# app.py _set_terminal_sessions
self._current_sessions = sessions  # keep None as sentinel

# _propagate_terminal_auto_remove
if self._current_sessions is None:
    return  # iTerm2 unreachable — skip removal
if not self._current_sessions:
    return  # genuinely empty — also skip (safety guard for "all tabs closed")
```

---

### WR-02: Stale session_id used in close/force-close after a rename

**File:** `src/joy/widgets/terminal_pane.py:481-491`, `530-549`

**Issue:** `action_close_session` and `action_force_close_session` capture `row.session_id`
at the time the key is pressed. They then push a `ConfirmationModal` and, when the user
confirms, call `_do_close_session(row.session_id, row.session_name, force=...)`. There is a
time window between key press and modal confirm during which a background `_load_terminal`
refresh could rebuild `self._rows`, replacing `row` with a new `SessionRow` object. The
captured `row` reference is now stale (it is a detached widget), but `row.session_id` is
still the correct value because it was captured by closure before rebuild.

This is actually safe for the `session_id` (it is an immutable string captured by value).
However, the `row.session_name` displayed in the confirmation modal may be stale if the
session was renamed between key press and confirm.

There is no crash or data loss here, but the user could see the wrong name in the
confirmation prompt if a rename happened in the background.

**Fix:** Capture both values as local variables before the modal push:

```python
def action_close_session(self) -> None:
    if self._cursor < 0 or self._cursor >= len(self._rows):
        return
    row = self._rows[self._cursor]
    session_id = row.session_id   # capture by value
    session_name = row.session_name  # capture by value
    from joy.screens import ConfirmationModal

    def on_confirm(confirmed: bool) -> None:
        if not confirmed:
            return
        self._do_close_session(session_id, session_name, force=False)

    self.app.push_screen(
        ConfirmationModal("Close Session", f"Close '{session_name}'?", ...),
        on_confirm,
    )
```

The same pattern applies to `action_force_close_session`.

---

### WR-03: `_update_linked_project_name` mutates TOML but does not refresh `_rel_index`

**File:** `src/joy/widgets/terminal_pane.py:467-479`

**Issue:** When a session is renamed, `_update_linked_project_name` updates `obj.value` in
the linked project and calls `_save_projects_bg()`. However, `self.app._rel_index` still
contains the old session name as the key in `_project_for_terminal`. Subsequent cross-pane
sync operations (e.g., `_sync_from_session(old_name)`) will still resolve the old name to a
project. After the next full refresh both `_load_terminal` and `_load_worktrees` recompute
the index, so the stale state is short-lived. But there is a window where:

1. User renames session "foo" → "bar"
2. `_rel_index._project_for_terminal` still maps "foo" → project
3. The terminal pane emits `SessionHighlighted("bar")`
4. `_sync_from_session("bar")` returns `None` — no sync happens for the renamed session

This means cross-pane sync is broken until the next refresh cycle completes.

**Fix:** After updating `obj.value`, also invalidate `_rel_index` or rebuild the terminal
part of it:

```python
def _update_linked_project_name(self, old_name: str, new_name: str) -> None:
    ...
    for obj in project.objects:
        if obj.kind == PresetKind.TERMINALS and obj.value == old_name:
            obj.value = new_name
            break
    self.app._save_projects_bg()
    # Force rel_index rebuild on next data load
    self.app._sessions_ready = False
    self.app._worktrees_ready = False
    # OR: trigger an immediate refresh
    self.app.call_from_thread(self.app._load_terminal)
```

Actually, `_do_rename_session` already calls `self.app.call_from_thread(self.app._load_terminal)`
after calling `_update_linked_project_name`. But since both are dispatched via
`call_from_thread`, their ordering on the main thread is not guaranteed. If `_load_terminal`
completes and resets `_rel_index` *before* `_update_linked_project_name` runs, the resolver
will use the old obj.value ("foo") from TOML and map "foo" → project again. The TOML save
happens in background too. The sequence is: (1) `_load_terminal` fetches sessions (new name
"bar"), (2) `_update_linked_project_name` changes obj.value to "bar" in memory, (3) the
resolver runs and sees obj.value = "bar" — this actually works correctly *if* step 2 happens
before the resolver pass. But `call_from_thread` ordering is FIFO on the Textual event queue,
so these two calls will execute in source order: `_update_linked_project_name` first, then
`_load_terminal` fires the worker. So the ordering is actually safe in practice.

The actual remaining bug: `_rel_index._project_for_terminal` still has "foo" as key until
the new `_load_terminal` worker completes its full fetch-and-set cycle. During that window
(which may be several seconds), sync-from-session for "bar" returns None.

**Severity:** Low-impact (short window, eventually consistent), but worth noting.

---

### WR-04: `create_session` in `terminal_sessions.py` does not handle `tab.sessions` being empty

**File:** `src/joy/terminal_sessions.py:122-124`

**Issue:** After `window.async_create_tab()`, the code accesses `tab.sessions[0]` without
checking whether `sessions` is non-empty. The iTerm2 API's `async_create_tab()` is
documented to return a `Tab` object, and `Tab.sessions` should always contain at least one
session, but this assumption is not guarded.

The same pattern exists in `_open_iterm` in `operations.py` at line 101.

**Fix:**

```python
tab = await window.async_create_tab()
if tab is None:
    return
if not tab.sessions:
    return   # defensive guard
session = tab.sessions[0]
await session.async_set_name(name)
result = session.session_id
```

---

### WR-05: `_open_iterm` in `operations.py` raises `RuntimeError` on failure but callers may silently swallow it

**File:** `src/joy/operations.py:107`

**Issue:** `_open_iterm` raises `RuntimeError(f"Failed to open iTerm2 session '{name}'")` if
`success` is `False` after `Connection().run_until_complete()` returns. However, the `_do_open`
worker in `project_detail.py` catches all `Exception` and shows a generic "Failed to open"
toast. This is fine for user experience, but there is a separate path: `_open_defaults` in
`app.py` (line 843-844) also catches all `Exception` and appends to an error list. So the
RuntimeError is always handled. No crash.

However, in `_open_iterm`, if `Connection().run_until_complete(_open)` itself raises (e.g.,
`ConnectionRefusedError`), the exception propagates out of `_open_iterm` uncaught (no
try/except around the `Connection().run_until_complete` call, unlike the analogous pattern in
`terminal_sessions.py` which wraps it in `try/except Exception`). The caller's broad
`except Exception` will catch it, but the inconsistency between `operations.py` and
`terminal_sessions.py` is a code quality issue that could cause surprising behaviour if the
call site changes.

**Fix:** Wrap the `Connection().run_until_complete` call in `_open_iterm` with a try/except,
consistent with `terminal_sessions.py`:

```python
try:
    Connection().run_until_complete(_open, retry=False)
except Exception:
    pass
if not success:
    raise RuntimeError(f"Failed to open iTerm2 session '{name}'")
```

---

## Info

### IN-01: `PresetKind.TERMINALS` uses plural but singular is conventional for enum members

**File:** `src/joy/models.py:30`

**Issue:** All other `PresetKind` members use singular nouns (`MR`, `BRANCH`, `TICKET`,
`WORKTREE`, etc.). `TERMINALS` is plural. This is a cosmetic inconsistency but can cause
surprising string output: `item.kind.value` returns `"terminals"` (plural) in toasts and
TOML.

**Fix:** Consider renaming to `TERMINAL` and updating the `PRESET_MAP` key and all
references. This is a low-priority naming consistency issue. The backward-compat migration
in `store.py` (`"agents"` → `"terminals"`) would need a corresponding update if renamed.

---

### IN-02: Duplicate `GroupHeader` class in `terminal_pane.py` and `worktree_pane.py`

**File:** `src/joy/widgets/terminal_pane.py:71-83`

**Issue:** The `GroupHeader` widget is defined identically (same CSS, same base class) in
both `terminal_pane.py` and `worktree_pane.py`. The comment at line 72 acknowledges this
("Duplicated from worktree_pane to avoid cross-widget coupling"). This is a code duplication
issue that will diverge over time if the header style changes.

**Fix:** Extract to a shared `src/joy/widgets/group_header.py` and import in both files.

---

### IN-03: `_detect_claude` uses case-insensitive "claude" match on `session.name` indirectly but not via session name

**File:** `src/joy/terminal_sessions.py:12-27`

**Issue:** The docstring at line 15 says "Session name is intentionally NOT used". However,
`_detect_claude` is called with `job` (the foreground process name) and `tty`. If a user
names a session "claude-work", the name is not checked. This is intentional and documented.
No bug, but if the intent changes, the function name `_detect_claude` might mislead
maintainers into thinking it checks the session name.

**No code change needed** — the docstring is clear. This is a documentation note only.

---

### IN-04: `action_edit_object` in `project_detail.py` re-uses `_save_toggle` for a rename

**File:** `src/joy/widgets/project_detail.py:257`

**Issue:** `action_edit_object` calls `self._save_toggle()` after updating `item.value`, but
`_save_toggle` is named for the "toggle open_by_default" operation. Reusing it for value
edits works correctly (it just persists `self.app._projects`), but the method name is
misleading. This is pre-existing code, not introduced in this changeset.

**Fix:** Rename `_save_toggle` to `_persist_projects` or `_save_projects` for clarity.

---

_Reviewed: 2026-04-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard (thorough)_
