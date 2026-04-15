---
phase: 15-cross-pane-selection-sync
plan: "02"
subsystem: sync
tags: [tdd, sync, cross-pane, green-phase, app-wiring]
dependency_graph:
  requires: [15-01]
  provides: [src/joy/app.py, src/joy/widgets/worktree_pane.py, src/joy/widgets/terminal_pane.py, src/joy/widgets/project_list.py]
  affects: [tests/test_sync.py]
tech_stack:
  added: []
  patterns: [_is_syncing boolean guard, sync_to() silent cursor mutation, try/finally guard pattern, Textual inner Message class pattern]
key_files:
  created: []
  modified:
    - src/joy/app.py
    - src/joy/widgets/worktree_pane.py
    - src/joy/widgets/terminal_pane.py
    - src/joy/widgets/project_list.py
    - tests/test_sync.py
key_decisions:
  - "_is_syncing boolean guard at app level prevents sync loops; all cursor handlers check it first before doing anything"
  - "sync_to() inline highlight path (CSS + scroll, no post_message) avoids Pitfall 1 — separate from _update_highlight() which posts messages"
  - "FakePane.sync_to() implementations updated in tests to match real widget interface — tests assert on _cursor position without requiring Textual DOM"
  - "test_sync_does_not_steal_focus uses inspect.getsource() + docstring stripping to verify no .focus() call in sync_to() code paths"
  - "RelationshipIndex imported at top level in app.py; _rel_index type annotation updated from object|None to RelationshipIndex|None"
metrics:
  duration: "~30 minutes"
  completed: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 5
---

# Phase 15 Plan 02: Core Sync Implementation Summary

**One-liner:** All six cross-pane sync directions (SYNC-01..06) wired via WorktreeHighlighted/SessionHighlighted messages and _is_syncing guard with try/finally — SYNC-01..07 GREEN.

## What Was Built

### Task 1: Message Classes, _is_syncing Guard, sync_to() Methods

**src/joy/app.py:**
- Added `self._is_syncing: bool = False` to `JoyApp.__init__` (Phase 15 D-03)
- Added `self._sync_enabled: bool = True` to `JoyApp.__init__` (Phase 15 D-12, needed by Task 2 handler logic)

**src/joy/widgets/worktree_pane.py:**
- Added `from textual.message import Message` import
- Added `WorktreePane.WorktreeHighlighted` inner Message class carrying a `WorktreeInfo` object (D-01, D-02)
- Extended `_update_highlight()` to post `WorktreeHighlighted` when `not getattr(self.app, "_is_syncing", False)` — prevents loop while allowing user-driven events to propagate
- Added `WorktreePane.sync_to(repo_name, branch)` — inline highlight-only path, no `post_message`, no `.focus()` (D-09, D-10)

**src/joy/widgets/terminal_pane.py:**
- Added `from textual.message import Message` import
- Added `TerminalPane.SessionHighlighted` inner Message class carrying `session_name: str` (D-01, D-02)
- Extended `_update_highlight()` to post `SessionHighlighted` with same `_is_syncing` guard
- Added `TerminalPane.sync_to(session_name)` — inline highlight-only path, no message, no focus

**src/joy/widgets/project_list.py:**
- Added `ProjectList.sync_to(project_name)` — iterates `_rows`, sets `_cursor`, applies highlight CSS inline. Explicitly does NOT use `select_index()` to avoid `_update_highlight()` re-posting `ProjectHighlighted` (Pitfall 1 prevention)

**tests/test_sync.py:**
- Replaced `pytest.fail()` bodies in `FakeWorktreePane.sync_to()`, `FakeTerminalPane.sync_to()`, `FakeProjectList.sync_to()` with real implementations mirroring the widget code — SYNC-01..06 tests now assert `_cursor` position correctly
- Updated `test_sync_does_not_steal_focus` to: import real widget classes, assert `hasattr(cls, "sync_to")`, inspect source with docstring-stripping to verify no `.focus()` call in code paths

### Task 2: Six Sync Handlers in JoyApp

**src/joy/app.py:**
- Added `from joy.resolver import RelationshipIndex` at top-level import
- Updated `_rel_index` type annotation: `object | None` → `RelationshipIndex | None`
- Extended `on_project_list_project_highlighted` to call `_sync_from_project()` when sync enabled and `_rel_index` is not None (Pitfall 2 guard)
- Added `_sync_from_project(project)` — sets `_is_syncing = True`, drives `WorktreePane.sync_to()` and `TerminalPane.sync_to()`, `finally: _is_syncing = False` (SYNC-01, SYNC-02)
- Added `on_worktree_pane_worktree_highlighted` handler (SYNC-03, SYNC-04)
- Added `_sync_from_worktree(worktree)` — resolves owning project via `_rel_index.project_for_worktree()`, drives `ProjectList.sync_to()` and `TerminalPane.sync_to()`
- Added `on_terminal_pane_session_highlighted` handler (SYNC-05, SYNC-06)
- Added `_sync_from_session(session_name)` — resolves owning project via `_rel_index.project_for_agent()`, drives `ProjectList.sync_to()` and `WorktreePane.sync_to()`

All three `_sync_from_*` helpers follow identical pattern: check `_rel_index is not None`, set `_is_syncing = True`, execute sync operations in `try` block, clear guard in `finally`.

## Verification Results

```
uv run pytest tests/test_sync.py -k "not toggle and not footer and not slow" -q
→ 7 passed, 2 deselected in 0.11s (SYNC-01..SYNC-07 all GREEN)

uv run pytest -m "not slow and not macos_integration" -q
→ 1 failed (pre-existing Plan 03 stub: test_toggle_sync_footer_visibility), 305 passed, 43 deselected
```

The single failure (`test_toggle_sync_footer_visibility`) is an intentional Plan 03 stub that was already failing before Plan 02 — it requires `app.check_action()` which Plan 03 will implement.

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: Message classes, _is_syncing, sync_to() | `74c1620` | src/joy/widgets/worktree_pane.py, terminal_pane.py, project_list.py, src/joy/app.py, tests/test_sync.py |
| Task 2: Six sync handlers in JoyApp | `a45d488` | src/joy/app.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing `from textual.message import Message` in worktree_pane.py**
- **Found during:** Task 1 test run
- **Issue:** `WorktreePane.WorktreeHighlighted(Message)` class definition raised `NameError: name 'Message' is not defined` — `Message` was not imported in `worktree_pane.py`
- **Fix:** Added `from textual.message import Message` to imports
- **Files modified:** src/joy/widgets/worktree_pane.py
- **Commit:** `74c1620`

**2. [Rule 1 - Bug] test_sync_does_not_steal_focus source inspection matched docstring text**
- **Found during:** Task 1 test run
- **Issue:** `inspect.getsource()` includes docstring text; the docstring said "Does NOT call .focus()" — so the `.focus()` substring check was finding the docstring, not an actual code call
- **Fix:** Added docstring-stripping logic to filter out non-code lines before the `.focus()` assertion check
- **Files modified:** tests/test_sync.py
- **Commit:** `74c1620`

## Known Stubs

`tests/test_sync.py::test_toggle_sync_footer_visibility` — intentional Plan 03 stub calling `pytest.fail("not implemented — requires app.check_action() in Plan 03")`. This is by design; Plan 03 will implement `check_action` + `refresh_bindings()` toggle.

`tests/test_sync.py::test_toggle_sync_key` — marked `@pytest.mark.slow`, intentional Plan 03 stub for TUI pilot test.

These stubs do not block the plan goal (all six sync directions wired and tested).

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes. All changes are in-memory TUI cursor mutation logic.

## Self-Check: PASSED

- [x] `src/joy/app.py` exists with `_sync_from_project`, `_sync_from_worktree`, `_sync_from_session` methods
- [x] `src/joy/widgets/worktree_pane.py` contains `class WorktreeHighlighted` and `def sync_to`
- [x] `src/joy/widgets/terminal_pane.py` contains `class SessionHighlighted` and `def sync_to`
- [x] `src/joy/widgets/project_list.py` contains `def sync_to`
- [x] Commit `74c1620` exists: `git log --oneline | grep 74c1620`
- [x] Commit `a45d488` exists: `git log --oneline | grep a45d488`
- [x] SYNC-01..SYNC-07: 7 tests pass
- [x] Full suite: 305 tests pass (1 pre-existing Plan 03 stub failure)
