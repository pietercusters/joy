---
phase: 19-service-extraction-backend-tests
plan: 01
status: complete
started: 2026-05-08
completed: 2026-05-08
---

# Plan 19-01 Summary: PaneCoordinator Extraction

## What was built
Extracted PaneCoordinator service from app.py handling all 6 cross-pane sync directions. Pure Python, zero Textual imports. Context manager for sync guard.

## Key files

### Created
- `src/joy/pane_coordinator.py` — PaneCoordinator with sync_from_project, sync_from_worktree, sync_from_session
- `tests/test_pane_coordinator.py` — 12 backend tests

### Modified
- `src/joy/app.py` — Delegates sync to coordinator, removed 3 sync methods + _is_syncing state (-76 lines)
- `src/joy/widgets/worktree_pane.py` — Updated getattr guard for coordinator
- `src/joy/widgets/terminal_pane.py` — Updated getattr guard for coordinator

## Deviations
None.

## Self-Check: PASSED
- 423 tests pass (411 existing + 12 new)
- Zero `_sync_from_*` methods remain in app.py
- Zero Textual imports in pane_coordinator.py
