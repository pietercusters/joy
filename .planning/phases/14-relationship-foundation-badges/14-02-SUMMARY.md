---
phase: 14-relationship-foundation-badges
plan: 02
subsystem: ui
tags: [textual, worktree-pane, terminal-pane, cursor, tdd]

# Dependency graph
requires:
  - phase: 12-iterm2-integration-terminal-pane
    provides: TerminalPane with set_sessions() and SessionRow widgets
  - phase: 09-worktree-pane
    provides: WorktreePane with set_worktrees() and WorktreeRow widgets
provides:
  - WorktreePane.set_worktrees() with identity-based cursor preservation (FOUND-03)
  - TerminalPane.set_sessions() with identity-based cursor preservation (FOUND-04)
  - SessionRow.session_name attribute for identity matching
  - Clamp fallback: min(saved_index, len-1) when item disappears (D-14)
affects:
  - 14-03-PLAN
  - phase-15-cross-pane-sync

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "saved_identity capture before DOM rebuild, restore by search after rebuild"
    - "min(saved_index, len(new_rows) - 1) clamp fallback when item is gone"

key-files:
  created:
    - tests/test_worktree_pane_cursor.py (extended with 2 slow identity tests)
    - tests/test_terminal_pane.py (extended with 1 unit + 2 slow identity tests)
  modified:
    - src/joy/widgets/worktree_pane.py (set_worktrees identity preservation)
    - src/joy/widgets/terminal_pane.py (SessionRow.session_name + set_sessions identity preservation)

key-decisions:
  - "Use (repo_name, branch) tuple as WorktreePane row identity — both fields already stored on WorktreeRow"
  - "Use session_name as TerminalPane row identity — required adding session_name to SessionRow.__init__"
  - "Clamp fallback to min(saved_index, len-1) rather than reset-to-0 when item disappears (D-14)"
  - "Identity capture done as local variables in async method — no class-level state needed"

patterns-established:
  - "Identity-based cursor preservation: save identity before remove_children(), restore after new_rows built"
  - "Clamp-not-reset: when saved item gone, min(saved_index, len-1) prevents jarring jump-to-top"

requirements-completed: [FOUND-03, FOUND-04]

# Metrics
duration: 15min
completed: 2026-04-14
---

# Phase 14 Plan 02: Relationship Foundation Badges Summary

**Identity-based cursor preservation in WorktreePane and TerminalPane: cursor survives DOM rebuilds by tracking (repo_name, branch) and session_name, with min(saved_index, len-1) clamp fallback when item disappears**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-14T19:07:00Z
- **Completed:** 2026-04-14T19:22:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- WorktreePane.set_worktrees() now preserves cursor on same (repo_name, branch) identity across DOM rebuilds triggered by background refresh (FOUND-03)
- TerminalPane.set_sessions() now preserves cursor on same session_name across DOM rebuilds (FOUND-04), requiring adding session_name attribute to SessionRow
- Both panes use min(saved_index, len-1) clamp fallback when the saved item disappears — cursor never jarring-resets to row 0
- 5 new tests added (2 slow TDD tests per pane, 1 unit test for session_name attribute); full suite 285 passing

## Task Commits

Each task was committed atomically:

1. **Task 1: WorktreePane cursor identity preservation (FOUND-03)** - `9ecb377` (feat)
2. **Task 2: TerminalPane cursor identity preservation + SessionRow.session_name (FOUND-04)** - `2889a52` (feat)

## Files Created/Modified

- `src/joy/widgets/worktree_pane.py` - Added saved_identity capture before DOM rebuild; identity-restore block after new_rows built
- `src/joy/widgets/terminal_pane.py` - Added session_name to SessionRow.__init__; saved_name capture + identity-restore in set_sessions()
- `tests/test_worktree_pane_cursor.py` - Added test_cursor_identity_preserved_across_set_worktrees_rebuild and test_cursor_clamps_when_item_gone_after_rebuild (both @pytest.mark.slow)
- `tests/test_terminal_pane.py` - Added test_session_row_stores_session_name (unit), test_cursor_identity_preserved_across_set_sessions_rebuild, test_cursor_clamps_when_session_gone_after_rebuild (both @pytest.mark.slow)

## Decisions Made

- Used (repo_name, branch) tuple as WorktreePane identity — both fields already on WorktreeRow, no changes to that class needed
- Required adding session_name to SessionRow since only session_id was stored previously
- Clamp fallback chosen over reset-to-0: when the highlighted item disappears, landing near the previous position is less jarring than jumping to top
- Identity vars are local to the async method — no class-level mutable state added, no thread-safety concerns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both panes now expose stable identity-based cursor state across DOM rebuilds
- Phase 15 (cross-pane sync) can rely on cursor pointing to the correct item after refresh
- No blockers — full suite 285 passing

## Self-Check: PASSED

All files verified present. Both task commits (9ecb377, 2889a52) confirmed in git log.

---
*Phase: 14-relationship-foundation-badges*
*Completed: 2026-04-14*
