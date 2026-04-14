---
phase: 14-relationship-foundation-badges
plan: 03
subsystem: ui
tags: [textual, badges, resolver, project-list]

requires:
  - phase: "14-01"
    provides: "RelationshipIndex with worktrees_for() and agents_for() pure functions"
  - phase: "14-02"
    provides: "Cursor identity preservation in WorktreePane and TerminalPane"

provides:
  - "ProjectRow with set_counts(wt_count, agent_count) — badge display layer"
  - "ProjectList.update_badges(index) — iterates rows and pushes counts"
  - "JoyApp._maybe_compute_relationships() — fires after both workers complete cycle"
  - "JoyApp._update_badges() — pushes RelationshipIndex to ProjectList"
  - "6 unit tests for badge display in tests/test_project_list.py"

affects: [future phases touching project-list, app refresh cycle, badge display]

tech-stack:
  added: []
  patterns:
    - "Two ready-flag pattern: _worktrees_ready + _sessions_ready guard _maybe_compute_relationships()"
    - "Flags reset before computing to prevent stale-data on next cycle"
    - "Lazy import of compute_relationships inside _maybe_compute_relationships (avoids circular at module level)"

key-files:
  created:
    - "tests/test_project_list.py"
  modified:
    - "src/joy/widgets/project_list.py"
    - "src/joy/app.py"

key-decisions:
  - "ICON_BRANCH and ICON_CLAUDE imported at module level in project_list.py (no circular import)"
  - "update_badges() uses lazy import of RelationshipIndex inside body to avoid circular at module level"
  - "_maybe_compute_relationships resets flags BEFORE computing (not after) to avoid missing a cycle"
  - "set_counts() calls Static.update() directly — no DOM rebuild, no widget remounting"

patterns-established:
  - "ProjectRow content always includes both icons even at zero count (D-10: consistent row width)"
  - "Two-flag synchronization: both data sources must report ready before computing cross-pane index"

requirements-completed: [BADGE-01, BADGE-02, BADGE-03, FOUND-01, FOUND-02, FOUND-03, FOUND-04]

duration: 25min
completed: 2026-04-14
---

# Plan 14-03: Badge Wiring Summary

**Live worktree and agent badge counts on every ProjectRow, updating after each background refresh cycle via two-flag resolver coordination**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-04-14
- **Tasks:** 3 (2 automated + 1 human checkpoint)
- **Files modified:** 3

## Accomplishments
- `ProjectRow` displays `{ICON_BRANCH} N  {ICON_CLAUDE} M` badge counts, always shown even at zero
- `ProjectRow.set_counts()` updates content in-place via `Static.update()` — no DOM rebuild
- `ProjectList.update_badges(index)` iterates all rows and pushes counts from `RelationshipIndex`
- `JoyApp._maybe_compute_relationships()` fires only when both `_worktrees_ready` and `_sessions_ready` are true, resets flags before computing
- `JoyApp._update_badges()` pushes the computed index to ProjectList
- Human verified: badge counts visible on project rows, cursors survive refresh without jumping

## Task Commits

1. **Task 1: ProjectRow badge display** — `cc0b903` (feat)
2. **Task 2: App-level badge wiring** — `7572d38` (feat)
3. **Task 3: Human verification** — approved

## Files Created/Modified
- `tests/test_project_list.py` — 6 unit tests covering badge icon visibility, set_counts(), zero counts
- `src/joy/widgets/project_list.py` — ICON imports, ProjectRow badge content, set_counts(), update_badges()
- `src/joy/app.py` — 5 new instance vars, _set_worktrees/_set_terminal_sessions instrumented, _maybe_compute_relationships(), _update_badges()

## Decisions Made
- Flags reset before computing (not after) — prevents a second cycle from being ignored if both workers fire rapidly
- `sessions or []` in `_set_terminal_sessions` — handles iTerm2 unavailable case cleanly (no NoneType errors in resolver)
- Lazy import of `compute_relationships` inside `_maybe_compute_relationships` — avoids circular import at app startup

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
- `Static.renderable` does not exist in Textual 8.x — plan tests used `row.renderable`, adjusted to `row.content` (the public property). All 6 tests green.

## Next Phase Readiness
- Full Phase 14 delivered: resolver (01), cursor preservation (02), badge display with app wiring (03)
- Human verified: badges visible, cursors stable across refresh cycles
- Ready for Phase 15

---
*Phase: 14-relationship-foundation-badges*
*Completed: 2026-04-14*
