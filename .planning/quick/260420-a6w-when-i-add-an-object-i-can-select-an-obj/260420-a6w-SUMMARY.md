---
phase: quick-260420-a6w
plan: 01
subsystem: screens
tags: [ux, modal, picker, filter-removal]
dependency_graph:
  requires: []
  provides: [PresetPickerModal without filter, RepoPickerModal without filter]
  affects: [src/joy/screens/preset_picker.py, src/joy/screens/repo_picker.py, tests/test_screens.py]
tech_stack:
  added: []
  patterns: [ListView focus-on-mount, direct index into static options list]
key_files:
  created: []
  modified:
    - src/joy/screens/preset_picker.py
    - src/joy/screens/repo_picker.py
    - tests/test_screens.py
decisions:
  - "Use ALL_PRESETS direct index in on_list_view_selected — no _filtered indirection needed since list is always complete"
  - "Focus ListView on mount (not Input) — immediately keyboard-navigable without Tab"
metrics:
  duration: ~5 minutes
  completed: 2026-04-20
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase quick-260420-a6w Plan 01: Remove filter Input from picker modals — Summary

**One-liner:** Stripped type-to-filter Input widget from both picker modals so the ListView receives focus immediately on open — no Tab required to navigate.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Strip filter Input from PresetPickerModal and RepoPickerModal | 95c81d3 | preset_picker.py, repo_picker.py |
| 2 | Remove filter tests; verify suite | 7783352 | tests/test_screens.py |

## What Changed

**preset_picker.py:**
- Removed `Input` widget import and `from textual.events import Key` import
- Removed `self._filtered` state from `__init__`
- Removed `yield Input(...)` from `compose`
- `on_mount` now calls `self.query_one("#preset-list", ListView).focus()`
- Deleted `on_input_changed`, `on_key`, `on_input_submitted` methods
- `on_list_view_selected` now indexes directly into `self.ALL_PRESETS`

**repo_picker.py:**
- Same removals as above — Input, Key, `_filtered`, filter event handlers
- `on_mount` now calls `self.query_one("#repo-list", ListView).focus()`
- `on_list_view_selected` now indexes directly into `self._options`

**tests/test_screens.py:**
- Deleted `test_preset_picker_filter`
- Deleted `test_repo_picker_select_none_returns_none`
- Deleted `test_repo_picker_filter_and_select`
- 23 remaining tests pass (10.33s)

## Verification

- `uv run python -c "from joy.screens.preset_picker import PresetPickerModal; from joy.screens.repo_picker import RepoPickerModal; print('imports ok')"` — passed
- `uv run python -m pytest tests/test_screens.py -x -q --tb=short` — 23 passed
- No `Input`, `Key`, `_filtered`, `on_input_`, `on_key`, or `filter` references remain in either modal file

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `src/joy/screens/preset_picker.py` exists and imports cleanly
- [x] `src/joy/screens/repo_picker.py` exists and imports cleanly
- [x] `tests/test_screens.py` — 3 filter tests deleted, 23 remaining pass
- [x] Commit `95c81d3` exists (Task 1)
- [x] Commit `7783352` exists (Task 2)
