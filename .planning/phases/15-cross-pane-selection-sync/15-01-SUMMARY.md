---
phase: 15-cross-pane-selection-sync
plan: "01"
subsystem: tests
tags: [tdd, sync, test-scaffold, red-phase]
dependency_graph:
  requires: []
  provides: [tests/test_sync.py]
  affects: [tests/test_sync.py]
tech_stack:
  added: []
  patterns: [FakePane stub pattern, pure-Python TUI test pattern]
key_files:
  created:
    - tests/test_sync.py
  modified: []
key_decisions:
  - "FakePane stub classes (FakeWorktreePane, FakeTerminalPane, FakeProjectList) model _cursor/_rows pattern without requiring Textual widget instantiation — tests are pure Python, no display needed"
  - "test_sync_does_not_steal_focus fails RED with explicit message directing Plan 02 to implement sync_to on real widget classes — prevents confusion about test intent"
  - "SYNC-08 (test_toggle_sync_key) decorated with @pytest.mark.slow so default test run (addopts=-m 'not slow') excludes it — avoids TUI pilot requirement until Plan 03"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-15"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 0
---

# Phase 15 Plan 01: Cross-Pane Sync Test Scaffold Summary

**One-liner:** Pure-Python test scaffold for all 9 SYNC requirements using FakePane stub classes — 9 tests, all RED, imports cleanly, no Textual display required.

## What Was Built

`tests/test_sync.py` — the Wave 0 test scaffold for Phase 15 cross-pane selection sync. Contains 9 failing test stubs covering SYNC-01 through SYNC-09. All tests fail with `pytest.fail("not implemented")` — correct RED state.

### Test Coverage

| Test Function | Requirement | Path | Status |
|---------------|-------------|------|--------|
| test_sync_project_to_worktree | SYNC-01 | project → worktree | RED |
| test_sync_project_to_terminal | SYNC-02 | project → terminal | RED |
| test_sync_worktree_to_project | SYNC-03 | worktree → project | RED |
| test_sync_worktree_to_terminal | SYNC-04 | worktree → terminal | RED |
| test_sync_agent_to_project | SYNC-05 | agent → project | RED |
| test_sync_agent_to_worktree | SYNC-06 | agent → worktree | RED |
| test_sync_does_not_steal_focus | SYNC-07 | focus non-interference | RED |
| test_toggle_sync_key | SYNC-08 | key binding toggle | RED (@pytest.mark.slow) |
| test_toggle_sync_footer_visibility | SYNC-09 | footer visibility | RED |

### Key Patterns

**FakePane stub classes:** SYNC-01 through SYNC-06 tests use pure-Python stub classes (`FakeWorktreePane`, `FakeTerminalPane`, `FakeProjectList`) that hold `_cursor` and `_rows` lists but require no Textual widget instantiation. This allows assertions on cursor position without a TUI display context.

**Real resolver, fake panes:** Each test builds a real `RelationshipIndex` via `compute_relationships()` with real `WorktreeInfo`, `TerminalSession`, and `Project` objects. The fake panes are only used for cursor-position assertions. This ensures the resolver contracts are tested with real code.

**Stub structure:** Each test:
1. Builds resolver with 1 project→resource relationship
2. Builds fake pane with 3 rows — target at index 1
3. Calls `sync_to()` (fails RED)
4. Asserts `_cursor == 1` (plan 02 GREEN target)
5. Tests "no match" case (cursor unchanged)

## Verification Results

```
uv run pytest tests/test_sync.py --collect-only -q
→ 8 tests collected, 1 deselected (slow), 0 errors

uv run pytest tests/test_sync.py -q
→ 8 failed, 1 deselected, exit code 1 (RED confirmed)

uv run pytest -m "not slow and not macos_integration" -q
→ 8 failed, 298 passed, 43 deselected (existing suite unbroken)
```

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: Write failing test scaffold (RED) | `5c5659d` | tests/test_sync.py |

## Deviations from Plan

None — plan executed exactly as written.

The plan's acceptance criteria specified "9 tests collected" from `--collect-only -q`. The actual behavior is 8 collected (1 deselected) due to pytest's `addopts = ["-m", "not slow and not macos_integration"]` in `pyproject.toml`. Running with `-m ""` to override the filter shows all 9. This is the correct behavior — the slow test is excluded by design (per the plan: "mark with @pytest.mark.slow").

## Known Stubs

All 9 test functions are intentional stubs by design — this is the TDD RED phase. Plan 02 will implement `sync_to()` on the real widget classes, turning SYNC-01..06 GREEN. Plan 03 will implement the TUI pilot tests for SYNC-07..09.

## Threat Flags

None — test code only, no new network endpoints, auth paths, or production file modifications.

## Self-Check: PASSED

- [x] `tests/test_sync.py` exists at expected path
- [x] Commit `5c5659d` exists (`git log --oneline | grep 5c5659d`)
- [x] 9 tests collected with `-m ""`
- [x] All tests fail RED (exit code 1)
- [x] Existing 298 tests still pass
