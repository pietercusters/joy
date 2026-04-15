---
phase: 16-live-data-propagation
reviewed: 2026-04-15T09:01:49Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/joy/app.py
  - src/joy/models.py
  - src/joy/widgets/object_row.py
  - src/joy/widgets/project_detail.py
  - src/joy/widgets/project_list.py
  - src/joy/widgets/terminal_pane.py
  - src/joy/widgets/worktree_pane.py
  - tests/test_propagation.py
  - tests/test_terminal_pane.py
  - tests/test_worktree_pane_cursor.py
  - tests/conftest.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-04-15T09:01:49Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 16 adds two propagation methods (`_propagate_mr_auto_add`, `_propagate_agent_stale`) to `JoyApp`, wires them together in `_propagate_changes`, and applies a `--stale` CSS class to `ObjectRow` for offline agents. Three files listed in the config did not exist at review time (`src/joy/resolver.py`, `tests/test_project_list.py`, `tests/test_resolver.py`, `tests/test_sync.py`) and were skipped; the remaining 11 files were read in full.

The propagation logic itself is correct and well-tested. Three warnings deserve attention before ship: a stale-row-access race in `_propagate_changes`, a fragile string-scan used to distinguish MR additions from agent messages, and a missing `_is_syncing` guard on the `notify()` calls that precede the pane rebuild. The info items are minor.

---

## Warnings

### WR-01: Stale `_rows` access immediately after deferred `set_projects`

**File:** `src/joy/app.py:317-321`

**Issue:** `_propagate_changes` calls `project_list.set_projects(...)` (line 318) then immediately reads `project_list._rows` and `project_list._cursor` (lines 319-320) to decide which project to push to `ProjectDetail`. However, `set_projects` schedules its rebuild via `call_after_refresh` — the actual `_rows` list is not updated until the next render cycle. Lines 319-320 therefore read the *previous* row list, so `current` is the project that was highlighted before propagation, not the project highlighted after the rebuild completes. In practice the old and new rows map to the same projects (no insertions or reorderings occur during agent-stale-only propagation), so this is benign today. But if a future change causes row reordering (e.g., repo grouping after MR auto-add changes a project's `repo` field), the detail pane would show the wrong project silently.

**Fix:** Drive `ProjectDetail` from inside the deferred `_rebuild` callback, or use `call_after_refresh` for the `set_project` call:

```python
# Option A: defer the detail pane update to after _rebuild completes
if messages:
    self._is_syncing = True
    try:
        project_list = self.query_one(ProjectList)
        project_list.set_projects(self._projects, self._repos)
        # cursor/rows are valid only after rebuild; defer to next frame
        def _sync_detail() -> None:
            if project_list._cursor >= 0 and project_list._cursor < len(project_list._rows):
                current = project_list._rows[project_list._cursor].project
                self.query_one(ProjectDetail).set_project(current)
        project_list.call_after_refresh(_sync_detail)
    finally:
        self._is_syncing = False
```

---

### WR-02: Fragile unicode-string scan to detect MR additions

**File:** `src/joy/app.py:305`

**Issue:** Whether to trigger a TOML save is determined by scanning the human-readable message strings for the Unicode character `⊕` followed by "Added PR":

```python
mr_added = any("\u2295 Added PR" in m for m in messages)
```

This couples the save decision to the exact formatting of notification strings. If the MR message format ever changes (e.g., internationalisation, rebranding "PR" to "MR", or a refactor of `_propagate_mr_auto_add`), the save silently stops triggering with no compile-time or test-time signal.

**Fix:** Return a structured result from `_propagate_mr_auto_add` instead of relying on message text parsing. The simplest approach is a separate boolean or a named tuple:

```python
def _propagate_mr_auto_add(self, mr_data: dict) -> tuple[list[str], bool]:
    """Returns (messages, any_added)."""
    ...
    return messages, len(messages) > 0  # messages only exist for adds

# in _propagate_changes:
mr_messages, mr_added = self._propagate_mr_auto_add(mr_data)
messages.extend(mr_messages)
...
if mr_added:
    self._save_projects_bg()
```

---

### WR-03: `notify()` calls fire outside the `_is_syncing` guard

**File:** `src/joy/app.py:309-311`

**Issue:** Notifications are emitted (lines 309-311) before `_is_syncing` is set to `True` (line 315). In the Textual event loop, `notify()` dispatches a message synchronously onto the event queue. If any message handler reacts to a notification and triggers a `ProjectHighlighted` or similar message before the `_is_syncing = True` block is reached, the cross-pane sync guard is ineffective during that window.

While Textual processes messages one at a time and `notify` only enqueues a toast (it does not immediately call any user handler), the ordering assumption is implicit and not enforced. The `_is_syncing = True` block should wrap the entire mutation-visible section including notifications:

```python
if messages:
    self._is_syncing = True
    try:
        for msg in messages:
            self.notify(msg, markup=False)
        project_list = self.query_one(ProjectList)
        project_list.set_projects(self._projects, self._repos)
        ...
    finally:
        self._is_syncing = False
```

---

## Info

### IN-01: `getattr(item, 'stale', False)` defensive call is unnecessary

**File:** `src/joy/widgets/project_detail.py:157`

**Issue:** `stale` is a declared dataclass field on `ObjectItem` with a default of `False`. Using `getattr(item, 'stale', False)` implies uncertainty about whether the field exists. This is safe but misleading — it suggests the attribute may be absent, when in fact it always exists.

**Fix:** Use a direct attribute access:

```python
if item.stale:
    row.add_class("--stale")
```

The same pattern appears in the test fixtures (e.g., `tests/test_propagation.py:378, 388, 395, 407`) and should be updated there too for consistency.

---

### IN-02: Tests replicate production logic instead of testing it

**File:** `tests/test_propagation.py:373-411` (class `TestStaleCSSIntegration`)

**Issue:** The `TestStaleCSSIntegration` tests manually reproduce the stale-class application logic from `_render_project` (the `if getattr(item, 'stale', False): row.add_class("--stale")` pattern) rather than calling the real `_render_project`. This means the tests would pass even if `_render_project` lost its stale-class application entirely. They test what the test author *wrote* rather than what the production code *does*.

**Fix:** Either (a) call `_render_project` through a minimal mounted `ProjectDetail` widget (as the existing async tests in `test_terminal_pane.py` do), or (b) add an explicit note that these tests are unit-testing the `ObjectRow` construction behaviour in isolation and the production wiring is covered by integration tests. If no integration test covers the `_render_project` stale path, add one.

---

### IN-03: Three files listed in review config do not exist

**Files:** `src/joy/resolver.py`, `tests/test_project_list.py`, `tests/test_resolver.py`, `tests/test_sync.py`

**Issue:** These files were listed in the `files` config block but do not exist on disk. `src/joy/resolver.py` was deleted as part of Phase 16 (the import was removed from `app.py`). The test files were presumably planned but not yet created. This is not a code defect, but it indicates three test files expected by the phase plan are absent: `test_project_list.py` (ProjectList widget unit tests), `test_resolver.py` (resolver tests — now deleted with the resolver), and `test_sync.py` (cross-pane sync tests).

**Fix:** Either create the missing test files or remove them from the phase review config. If the resolver was intentionally deleted, `test_resolver.py` should be confirmed as no longer needed.

---

_Reviewed: 2026-04-15T09:01:49Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
