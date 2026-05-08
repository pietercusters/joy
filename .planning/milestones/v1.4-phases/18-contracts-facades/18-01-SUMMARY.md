---
phase: 18-contracts-facades
plan: 01
status: complete
started: 2026-05-08
completed: 2026-05-08
---

# Plan 18-01 Summary: Protocol Contracts & Widget Facades

## What was built
Created `src/joy/ports.py` with 5 `@runtime_checkable` Protocol classes defining typed service boundaries. Added public facade properties/methods to all 4 widget panes.

## Key files

### Created
- `src/joy/ports.py` — StoragePort (8 methods), GitDataPort (1), TerminalPort (7), OpenerPort (1), SyncablePane (2)

### Modified
- `src/joy/widgets/project_detail.py` — Added `current_project`, `default_items`, `clear()`
- `src/joy/widgets/project_list.py` — Added `current_project`
- `src/joy/widgets/worktree_pane.py` — Added `highlighted_worktree`
- `src/joy/widgets/terminal_pane.py` — Added `highlighted_session`

## Deviations
None. All additions are pure — no existing behavior changed.

## Self-Check: PASSED
- All 5 Protocols importable from joy.ports
- All 402 existing tests pass
- SyncablePane uses `*args: str` to accommodate both WorktreePane and TerminalPane signatures
