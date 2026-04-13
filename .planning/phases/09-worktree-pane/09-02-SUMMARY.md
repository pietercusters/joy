---
phase: 09-worktree-pane
plan: 02
subsystem: worktree-pane
tags: [tdd, implementation, wave-2, green-phase]
dependency_graph:
  requires: [09-01]
  provides: [src/joy/widgets/worktree_pane.py, src/joy/app.py]
  affects: [phase-10-refresh-timer, phase-11-mr-ci-indicators]
tech_stack:
  added: []
  patterns: [rich-text-multiline-rows, work-thread-call-from-thread, verticalscroll-non-focusable]
key_files:
  created: []
  modified:
    - src/joy/widgets/worktree_pane.py
    - src/joy/app.py
    - tests/test_worktree_pane.py
    - tests/test_pane_layout.py
decisions:
  - "WorktreeRow accepts WorktreeInfo directly (not rich.Text) so tests can call WorktreeRow(wt) — display_path override kwarg allows pane to apply middle_truncate before construction"
  - "GroupHeader duplicated from project_detail.py (not imported) to avoid cross-widget coupling — 10-line class, low cost"
  - "Dirty indicator uses 'yellow' rich style (not '$warning' CSS var) — CSS variables are not valid in rich.Text style parameters"
  - "mock_store fixture in test_pane_layout.py extended with load_repos/discover_worktrees mocks to prevent filesystem access during Phase 8 regression tests"
  - "test_stub_panes_show_coming_soon updated: WorktreePane no longer shows 'coming soon' — now a live pane"
metrics:
  duration: ~15 minutes
  completed: "2026-04-13T09:57:21Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 4
---

# Phase 9 Plan 02: Implement WorktreePane (Wave 2 GREEN Phase) Summary

**One-liner:** Full WorktreePane implementation with grouped worktree rows, Nerd Font indicators, empty states, middle-truncated paths, and app-level threaded data loading worker.

## Objective

Replace the Phase 8 "coming soon" stub with a live, grouped worktree display. Data flows from `discover_worktrees()` through a background worker into `WorktreePane.set_worktrees()`, which builds grouped `GroupHeader` + `WorktreeRow` children sorted alphabetically.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement WorktreePane widget with rows, headers, empty states, path utilities | ccb5590 | src/joy/widgets/worktree_pane.py, tests/test_worktree_pane.py |
| 2 | Wire app-level worktree loading worker into JoyApp | f1d37a7 | src/joy/app.py, tests/test_pane_layout.py |

## What Was Built

### Task 1: WorktreePane Widget (`src/joy/widgets/worktree_pane.py`)

Complete rewrite of the Phase 8 stub. The file now contains:

**Pure path utilities:**
- `abbreviate_home(path_str)` — replaces leading `Path.home()` prefix with `~` (D-13)
- `middle_truncate(path, max_width)` — preserves `~/first-segment/…/leaf-segment` shape for long paths (D-14)

**Nerd Font icon constants:**
- `ICON_BRANCH = "\ue0a0"` — nf-pl-branch
- `ICON_DIRTY = "\uf111"` — nf-fa-circle (colored yellow in rich.Text)
- `ICON_NO_UPSTREAM = "\U000f0be1"` — nf-md-cloud_off (dim)

**Widget classes:**
- `_WorktreeScroll(VerticalScroll, can_focus=False)` — non-focusable scroll container (prevents Tab-focus theft, Pitfall 1)
- `GroupHeader(Static)` — repo section header with bold/muted styling (duplicated from project_detail, not imported)
- `WorktreeRow(Static)` — two-line row: branch + indicators on line 1, abbreviated path on line 2 (height: 2)
- `WorktreePane(Widget, can_focus=True)` — main pane with `set_worktrees()`, `BINDINGS=[]`, `border_title="Worktrees"`

**Key behaviors:**
- `set_worktrees(worktrees, *, repo_count=0, branch_filter="")` — idempotent, groups by `repo_name`, sorts repos and branches case-insensitively (D-11, D-12)
- Empty state D-15: "No repos registered. Add one via settings." when `repo_count == 0`
- Empty state D-16: "No active worktrees. (filtered: {branch_filter})" when repos exist but no worktrees
- Loading placeholder "Loading…" shown before first `set_worktrees` call (D-05)
- Broad `WorktreePane Static { ... }` selector removed; scoped `.empty-state` class used instead (Pitfall 6)

### Task 2: App-Level Worker (`src/joy/app.py`)

Additive changes only — no existing code removed:
- Added `WorktreeInfo` to model imports
- Added `_load_worktrees()` `@work(thread=True)` worker: lazy-imports `load_repos` and `discover_worktrees`, calls `_set_worktrees` via `call_from_thread` with `repo_count` and `branch_filter` args
- Added `_set_worktrees()` thin dispatcher that calls `WorktreePane.set_worktrees()`
- Modified `_set_projects()`: appended `self._load_worktrees()` call at end (fires after config is guaranteed available, D-02)

## Verification Results

- `uv run pytest tests/test_worktree_pane.py -x -q` — 17 passed
- `uv run pytest tests/test_pane_layout.py -x -q` — 9 passed
- `uv run pytest -q` — 214 passed, 1 deselected (full regression suite green)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed asyncio.get_event_loop() incompatibility with Python 3.14**
- **Found during:** Task 1 — first test run
- **Issue:** 5 unit tests used `asyncio.get_event_loop().run_until_complete()` which raises `RuntimeError` in Python 3.12+ when no event loop exists in the main thread
- **Fix:** Replaced all 5 occurrences with `asyncio.run()` in `tests/test_worktree_pane.py`
- **Files modified:** `tests/test_worktree_pane.py`
- **Commit:** ccb5590

**2. [Rule 1 - Bug] Fixed Static attribute name: `renderable` -> `content`**
- **Found during:** Task 1 — test run
- **Issue:** 2 test assertions used `h.renderable` on GroupHeader widgets; `Static` in Textual 8.x exposes `content`, not `renderable`
- **Fix:** Replaced `h.renderable` with `h.content` in `tests/test_worktree_pane.py`
- **Files modified:** `tests/test_worktree_pane.py`
- **Commit:** ccb5590

**3. [Rule 1 - Bug] Fixed rich.Text style parameter: `$warning` -> `yellow`**
- **Found during:** Task 1 — test run showing `rich.errors.MissingStyle: Failed to get style '$warning'`
- **Issue:** Textual CSS theme variables (e.g., `$warning`) are not valid style names in `rich.Text.append()`. Rich has its own style system that only understands standard color names and attributes.
- **Fix:** Changed `style="$warning"` to `style="yellow"` for the dirty indicator in `WorktreeRow.build_content()`
- **Files modified:** `src/joy/widgets/worktree_pane.py`
- **Commit:** ccb5590

**4. [Rule 1 - Bug] Updated Phase 8 layout test that broke after WorktreePane stub was filled**
- **Found during:** Task 2 — running regression suite
- **Issue:** `test_stub_panes_show_coming_soon` in `test_pane_layout.py` expected `"coming soon"` in the worktrees pane, but Phase 9 replaces the stub with a live pane showing empty-state messages
- **Fix:** Updated the test to only check `TerminalPane` for "coming soon" and verify `WorktreePane` exists with at least one Static widget. Also added `load_repos` and `discover_worktrees` mocks to the `mock_store` fixture to prevent real filesystem access.
- **Files modified:** `tests/test_pane_layout.py`
- **Commit:** f1d37a7

**5. [Rule 2 - Missing] WorktreeRow constructor accepts WorktreeInfo directly (not rich.Text)**
- **Found during:** Task 1 — test analysis
- **Issue:** Plan specified `WorktreeRow` passing `rich.Text` to `Static.__init__`, but tests call `WorktreeRow(wt)` where `wt` is a `WorktreeInfo`. The constructor must accept `WorktreeInfo`.
- **Fix:** `WorktreeRow.__init__` accepts `WorktreeInfo` as first arg plus optional `display_path` kwarg. The pane uses the `display_path` override to pass middle-truncated paths without double-abbreviating.
- **Files modified:** `src/joy/widgets/worktree_pane.py`
- **Commit:** ccb5590

## Known Stubs

None — all plan objectives are fully implemented and all 17 tests pass.

## Threat Flags

None — the implementation stays within the trust boundaries identified in the plan's threat model. All data flows through local git commands (Phase 7 contract) with existing timeout and silent-skip protections.

## Self-Check: PASSED

- [x] `src/joy/widgets/worktree_pane.py` exists and contains WorktreePane, WorktreeRow, GroupHeader, _WorktreeScroll, abbreviate_home, middle_truncate
- [x] `src/joy/app.py` contains _load_worktrees and _set_worktrees methods
- [x] Commit `ccb5590` exists (Task 1)
- [x] Commit `f1d37a7` exists (Task 2)
- [x] 17 Phase 9 tests pass
- [x] 214 total tests pass (full regression suite green)
