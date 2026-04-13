---
phase: 09-worktree-pane
plan: 01
subsystem: worktree-pane
tags: [tdd, test-first, wave-0, red-phase]
dependency_graph:
  requires: []
  provides: [tests/test_worktree_pane.py]
  affects: [plan-02-worktree-pane-implementation]
tech_stack:
  added: []
  patterns: [pytest-asyncio, textual-pilot, mock-store-fixture]
key_files:
  created:
    - tests/test_worktree_pane.py
  modified: []
decisions:
  - "Tests import WorktreeRow, GroupHeader, abbreviate_home, middle_truncate directly from joy.widgets.worktree_pane — will fail at import time until Plan 02 adds them (valid RED state)"
  - "Unit tests for grouping/ordering use a minimal _TestApp pattern with asyncio.get_event_loop().run_until_complete() to mount pane without full app overhead"
  - "Integration tests use same async pilot pattern as test_pane_layout.py: await pilot.pause(0.2) then await app.workers.wait_for_complete()"
metrics:
  duration: ~5 minutes
  completed: "2026-04-13T09:47:17Z"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 9 Plan 01: Create Phase 9 Test File (Wave 0 RED Phase) Summary

**One-liner:** 17-test RED phase test file for WorktreePane grouped display, indicators, empty states, and pure-function path utilities.

## Objective

Establish the automated verification contract for Phase 9 before any production code changes. Every subsequent task in Phase 9 uses these tests as its acceptance gate.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create complete test file for Phase 9 worktree pane | cfebba9 | tests/test_worktree_pane.py |

## What Was Built

Created `tests/test_worktree_pane.py` with 17 test functions covering all behaviors from VALIDATION.md:

**Unit tests (pure functions, no Textual app):**
- `test_path_abbreviation` — abbreviate_home replaces home dir with ~
- `test_middle_truncation` — middle_truncate preserves start/end for long paths
- `test_grouping_by_repo` — two repos produce two GroupHeaders
- `test_empty_repos_hidden` — repos with no worktrees produce no GroupHeader
- `test_repo_order_alphabetical` — repo sections sorted case-insensitively
- `test_worktree_order_alphabetical` — branches within a repo sorted case-insensitively
- `test_row_shows_branch` — WorktreeRow content contains branch name
- `test_dirty_indicator_shown` — dirty glyph (U+F111) present when is_dirty=True
- `test_no_upstream_indicator_shown` — no-upstream glyph (U+F0BE1) when has_upstream=False
- `test_clean_tracked_no_indicators` — neither glyph when clean + tracked
- `test_row_shows_abbreviated_path` — home-abbreviated path on row line 2
- `test_set_worktrees_idempotent` — calling set_worktrees twice produces identical DOM

**Integration tests (Textual pilot, async):**
- `test_loading_placeholder` — "Loading" Static shown before worker completes
- `test_app_loads_worktrees` — 4 WorktreeRow widgets after worker completes
- `test_empty_state_no_repos` — "No repos registered" when repos=[]
- `test_empty_state_no_worktrees` — "No active worktrees" when repos exist but no worktrees
- `test_pane_read_only` — BINDINGS==[] and can_focus=True

## Verification Results

- `uv run python -c "import ast; ast.parse(open('tests/test_worktree_pane.py').read())"` — syntax OK
- `grep -c 'def test_' tests/test_worktree_pane.py` — 17 (>= 17 required)
- `uv run pytest tests/ --ignore=tests/test_worktree_pane.py -q` — 197 passed (regression suite green)

## Deviations from Plan

None — plan executed exactly as written.

The tests import `WorktreeRow`, `GroupHeader`, `abbreviate_home`, `middle_truncate` from `joy.widgets.worktree_pane`. These symbols don't exist yet (valid RED state). The test file is syntactically correct and all assertions are well-formed — they will fail with ImportError or AttributeError until Plan 02 implements the production code.

## Known Stubs

None — this plan only creates tests. No stub patterns introduced.

## Threat Flags

None — this plan creates test files only. No new trust boundaries or security-relevant surfaces introduced.

## Self-Check: PASSED

- [x] `tests/test_worktree_pane.py` exists
- [x] Commit `cfebba9` exists: `git log --oneline | grep cfebba9`
- [x] 17 test functions counted
- [x] Existing 197 tests still pass
