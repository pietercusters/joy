---
phase: 20-widget-tests-snapshots
plan: 03
subsystem: testing
tags: [pytest-textual-snapshot, syrupy, svg-snapshots, visual-regression, snap_compare]

# Dependency graph
requires:
  - phase: 20-01
    provides: pytest-textual-snapshot dependency and snapshot marker in pyproject.toml
provides:
  - 3 SVG snapshot baselines for key TUI screens (initial render, project selected, sync active)
  - tests/test_snapshots.py with snap_compare-based snapshot tests
  - Visual regression detection via pytest --snapshot-update workflow
affects: [21-ui-polish, snapshot-ci]

# Tech tracking
tech-stack:
  added: []
  patterns: [snap_compare with run_before callbacks, store-level @patch for snapshot isolation, pytestmark module-level marker]

key-files:
  created:
    - tests/test_snapshots.py
    - tests/__snapshots__/test_snapshots/test_snapshot_initial_render.svg
    - tests/__snapshots__/test_snapshots/test_snapshot_project_selected.svg
    - tests/__snapshots__/test_snapshots/test_snapshot_sync_active.svg
  modified: []

key-decisions:
  - "SVG baselines stored in tests/__snapshots__/ (syrupy default) not tests/snapshot_tests_output/ (plan suggested)"
  - "Store-level @patch used for snapshot tests as pragmatic exception per RESEARCH.md Pitfall 2"

patterns-established:
  - "Snapshot tests are sync (no @pytest.mark.asyncio); run_before callbacks handle async internally"
  - "All snapshot tests use terminal_size=(120, 40) for consistent baselines"
  - "_mock_store() helper with patch.multiple and **kw lambdas for keyword-only store function signatures"

requirements-completed: [TEST-05]

# Metrics
duration: 2min
completed: 2026-05-08
---

# Phase 20 Plan 03: Snapshot Baseline Tests Summary

**3 SVG snapshot baselines (initial render, project selected, sync active) via pytest-textual-snapshot with deterministic store mocking**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-08T11:51:35Z
- **Completed:** 2026-05-08T11:54:07Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- Created tests/test_snapshots.py with 3 snapshot baseline tests covering initial render, project selection, and sync-active states
- Generated SVG baselines in tests/__snapshots__/test_snapshots/ that detect unintended visual regressions
- Verified baselines match on re-run (pytest without --snapshot-update passes)
- All 459 existing non-snapshot tests continue to pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create snapshot baseline tests** - `a59b92f` (test)

## Files Created/Modified
- `tests/test_snapshots.py` - 3 snapshot baseline tests using snap_compare with store-level @patch
- `tests/__snapshots__/test_snapshots/test_snapshot_initial_render.svg` - SVG baseline for initial render
- `tests/__snapshots__/test_snapshots/test_snapshot_project_selected.svg` - SVG baseline for project selected state
- `tests/__snapshots__/test_snapshots/test_snapshot_sync_active.svg` - SVG baseline for sync active state

## Decisions Made
- SVG baselines are stored in `tests/__snapshots__/` (syrupy/pytest-textual-snapshot default directory) rather than the `tests/snapshot_tests_output/` directory mentioned in the plan. This is the correct default behavior of the tool.
- Used `lambda **kw` in patch.multiple lambdas to match store functions' keyword-only `path` parameter signatures.

## Deviations from Plan

None - plan executed exactly as written. The baseline directory name difference (`__snapshots__` vs `snapshot_tests_output`) is simply the library's actual default, not a deviation from intended behavior.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Snapshot baselines are committed and verified
- Future phases can run `uv run pytest tests/test_snapshots.py -m snapshot` to detect visual regressions
- Regenerate baselines with `--snapshot-update` after intentional UI changes
- CI integration for snapshot tests deferred to ATEST-02

## Self-Check: PASSED

- tests/test_snapshots.py: FOUND
- tests/__snapshots__/test_snapshots/test_snapshot_initial_render.svg: FOUND
- tests/__snapshots__/test_snapshots/test_snapshot_project_selected.svg: FOUND
- tests/__snapshots__/test_snapshots/test_snapshot_sync_active.svg: FOUND
- Commit a59b92f: FOUND
- 20-03-SUMMARY.md: FOUND

---
*Phase: 20-widget-tests-snapshots*
*Completed: 2026-05-08*
