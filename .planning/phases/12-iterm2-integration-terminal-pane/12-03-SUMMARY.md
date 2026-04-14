---
phase: 12-iterm2-integration-terminal-pane
plan: "03"
subsystem: ui
tags: [textual, iterm2, terminal, refresh, workers]

requires:
  - phase: 12-01
    provides: fetch_sessions(), activate_session(), TerminalSession model
  - phase: 12-02
    provides: TerminalPane widget with set_sessions() and set_refresh_label()

provides:
  - _load_terminal() background worker wired into JoyApp refresh cycle
  - Terminal pane border_title timestamp and stale tracking independent of worktrees
  - r key and timer both trigger terminal + worktree refresh in parallel
  - Graceful degradation when iTerm2 unavailable (no crash, worktree unaffected)

affects: [future-phases-using-terminal-pane, phase-13-onwards]

tech-stack:
  added: []
  patterns:
    - Independent background workers per data source (D-15)
    - call_from_thread for bridging thread workers to UI updates
    - Separate refresh label tracking per pane

key-files:
  created: []
  modified:
    - src/joy/app.py
    - tests/test_refresh.py

key-decisions:
  - "_load_terminal uses lazy import of fetch_sessions inside worker to avoid top-level iTerm2 dependency"
  - "Terminal refresh tracking state (_terminal_last_refresh_at, _terminal_refresh_failed) kept separate from worktree tracking"
  - "_update_all_refresh_labels() combines both pane label updates under single timer callback"
  - "Claude idle vs active detection deferred — foreground_process alone cannot distinguish idle vs executing Claude"

patterns-established:
  - "Independent worker pattern: each data source gets its own @work(thread=True, exit_on_error=False) worker"
  - "Refresh label tracking: per-pane _last_refresh_at + _refresh_failed pair drives border_title"

requirements-completed: [TERM-05, TERM-06]

duration: ~30min
completed: 2026-04-14
---

# Plan 12-03: App Integration & Refresh Wiring Summary

**`_load_terminal()` worker wired into JoyApp — terminal pane refreshes in parallel with worktrees on mount, r key, and timer; border_title shows timestamp and stale state independently**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-04-14
- **Tasks:** 3 (2 auto + 1 human checkpoint)
- **Files modified:** 2

## Accomplishments
- Added `_load_terminal()` background worker to JoyApp with independent error handling (D-15)
- Wired terminal refresh into timer callback, r-key binding, and on_mount alongside worktrees
- Border_title timestamp and stale tracking for terminal pane via `_update_terminal_refresh_label()`
- 5 new tests covering terminal load on mount, r key trigger, unavailable state, independence from worktrees, and label updates (15 refresh tests total, all passing)
- Human verified: session grouping, j/k navigation, Enter-to-focus, Escape, r key refresh, and iTerm2-unavailable graceful degradation

## Task Commits

1. **Task 1: Wire _load_terminal into JoyApp refresh cycle** - `a0977c3` (feat)
2. **Task 2: Update refresh tests for terminal pane integration** - `0a81d93` (test)
   - fix: improve Claude session detection with multi-signal heuristic - `4e44107`
   - fix: remove session-name signal from Claude detection — too imprecise - `933cc55`
3. **Task 3: Visual verification** — human approved ✓

## Files Created/Modified
- `src/joy/app.py` — Added `_load_terminal`, `_set_terminal_sessions`, `_mark_terminal_refresh_success/failure`, `_update_terminal_refresh_label`, `_update_all_refresh_labels`; extended `_trigger_worktree_refresh`, `action_refresh_worktrees`, `_set_projects`
- `tests/test_refresh.py` — 5 new terminal pane integration tests

## Decisions Made
- Lazy import of `fetch_sessions` inside `_load_terminal` to avoid making iTerm2 a top-level startup dependency
- Separate `_terminal_last_refresh_at` / `_terminal_refresh_failed` state — keeps terminal and worktree tracking fully decoupled
- Combined `_update_all_refresh_labels()` as a single timer target for both panes
- Claude idle vs active detection deferred to future phase — not detectable from `foreground_process` alone (session-name signal also removed as too imprecise)

## Deviations from Plan
- Claude detection refinement: two fix commits after Task 1 tightened the `is_claude_session` heuristic and removed an unreliable session-name signal — within scope of the plan's Claude grouping requirement

## Issues Encountered
- Claude detection via session name was too imprecise (matched non-Claude sessions) — resolved by relying solely on `foreground_process` multi-signal heuristic

## Next Phase Readiness
- Phase 12 complete: iTerm2 integration data layer, UI, and app wiring all delivered
- Claude idle/active distinction deferred and noted for future phase

---
*Phase: 12-iterm2-integration-terminal-pane*
*Completed: 2026-04-14*
