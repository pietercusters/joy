---
phase: 05-settings-search-distribution
plan: "02"
subsystem: project-list-filter
tags: [filter, search, keyboard, tui, PROJ-06]
one_liner: "Real-time project list filter via / key with inline Input, case-insensitive substring match, Escape/Enter exit modes"

dependency_graph:
  requires: []
  provides: [PROJ-06-filter-mode]
  affects: [src/joy/widgets/project_list.py]

tech_stack:
  added: []
  patterns:
    - "Inline Input widget mounted above ListView via parent.mount(before=self)"
    - "_filter_active flag guards against duplicate Input mounts"
    - "Canonical project list never mutated; filter passes copies to set_projects()"
    - "on_key Escape handler with event.stop() prevents modal conflict (Pitfall 1)"

key_files:
  created:
    - tests/test_filter.py
  modified:
    - src/joy/widgets/project_list.py

decisions:
  - "Filter reads from self.app._projects (canonical) not self._projects (display) to prevent restoring filtered subset as truth"
  - "Escape uses on_key with event.stop() rather than a BINDING to avoid conflicting with ModalScreen Escape handling"
  - "set_projects() called with a copy (list()) on restore to avoid aliasing bugs"
  - "call_after_refresh(listview.focus) used after filter exit to restore focus after DOM mutation settles"

metrics:
  duration_minutes: 15
  completed_date: "2026-04-11"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 2
---

# Phase 05 Plan 02: Project List Filter Mode Summary

Real-time project list filter via `/` key with inline Input widget, case-insensitive substring match, Escape restores full list, Enter keeps filtered subset.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing filter tests | 4657de1 | tests/test_filter.py |
| GREEN | Filter implementation | e5eaa66 | src/joy/widgets/project_list.py |

## What Was Built

Modified `src/joy/widgets/project_list.py` to add filter mode:

- `JoyListView.BINDINGS` gains `Binding("/", "filter", "Filter", show=True)`
- `JoyListView._filter_active: bool = False` prevents duplicate mount
- `JoyListView.action_filter()` mounts `Input#filter-input` above the ListView and focuses it
- `ProjectList.on_input_changed()` filters `self.app._projects` in real-time by case-insensitive substring
- `ProjectList.on_input_submitted()` calls `_exit_filter_mode(restore=False)` — keeps filtered subset
- `ProjectList.on_key()` intercepts Escape when filter active, calls `_exit_filter_mode(restore=True)` with `event.stop()`
- `ProjectList._exit_filter_mode()` removes the Input widget, resets `_filter_active`, optionally restores canonical list, refocuses ListView

Created `tests/test_filter.py` with 7 integration tests covering all behaviors.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Model Compliance

- T-05-02-01 (Tampering — canonical list mutation): Mitigated. `on_input_changed` reads `self.app._projects` and passes a filtered copy to `set_projects()`. `_exit_filter_mode(restore=True)` does `list(self.app._projects)` — new list object every time.
- T-05-02-02 (DoS — DOM thrash): Accepted. Sub-millisecond for typical project counts.
- T-05-02-03 (Escape conflict): Mitigated. `on_key` with `_filter_active` guard + `event.stop()`.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Self-Check: PASSED

- [x] `tests/test_filter.py` exists
- [x] `src/joy/widgets/project_list.py` contains `action_filter`, `_filter_active`, `on_input_changed`, `on_input_submitted`, `on_key`, `_exit_filter_mode`
- [x] Commit 4657de1 exists (RED — failing tests)
- [x] Commit e5eaa66 exists (GREEN — implementation)
- [x] `uv run pytest tests/test_filter.py -x -q` — 7 passed
- [x] `uv run pytest tests/ -x -q` — 121 passed, no regressions
