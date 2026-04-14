---
phase: 03-activation
plan: 02
subsystem: ui
tags: [textual, keybindings, activation, toggle, toast, tdd, subprocess]

# Dependency graph
requires:
  - phase: 03-activation/03-01
    provides: ObjectRow.refresh_indicator(), _success_message(), _truncate(), JoyApp._config caching
  - phase: 02-tui-shell
    provides: ProjectDetail with cursor navigation, highlighted_object property
provides:
  - ProjectDetail.action_open_object wiring o key to open_object() in background thread
  - ProjectDetail.action_toggle_default wiring space key to flip open_by_default and persist
  - ProjectDetail._do_open worker running open_object in thread with success/error toast
  - ProjectDetail._save_toggle worker persisting toggle via save_projects in thread
  - 7 new tests covering ACT-01 and ACT-03 behaviours including failure paths
affects: [03-activation/03-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import inside @work thread: `from joy.operations import open_object` inside _do_open avoids import-time side effects and keeps worker self-contained"
    - "exit_on_error=False on all @work(thread=True) workers prevents subprocess failures from crashing TUI"
    - "markup=False on all app.notify() calls with user-supplied values prevents Rich markup injection"
    - "action_VERB / _do_VERB split: synchronous action_* validates and delegates, @work _do_* runs blocking I/O"

key-files:
  created:
    []
  modified:
    - src/joy/widgets/project_detail.py
    - tests/test_tui.py
    - tests/test_store.py

key-decisions:
  - "Lazy import of open_object and save_projects inside @work threads keeps module-level imports clean and avoids circular dependency risks"
  - "action_toggle_default updates dot indicator synchronously (in main loop) then persists asynchronously -- ensures immediate visual feedback per D-09"
  - "TDD RED commit captures both test files together (test_tui.py and test_store.py) since they test the same feature unit"

patterns-established:
  - "action_X / _do_X split pattern: synchronous guard in action_X (None check, error toast), async worker in _do_X for blocking I/O"
  - "All user-facing notify() calls use markup=False as a project-wide convention for safety"

requirements-completed: [ACT-01, ACT-03, CORE-05]

# Metrics
duration: 2min
completed: 2026-04-11
---

# Phase 03 Plan 02: o and space Key Bindings with Toast Feedback Summary

**ProjectDetail gains o (open object via subprocess in thread) and space (toggle open_by_default with dot refresh and TOML persist), both with markup-safe toast feedback and exit_on_error=False crash protection**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-11T07:49:05Z
- **Completed:** 2026-04-11T07:51:30Z
- **Tasks:** 1 (TDD: RED + GREEN + REFACTOR)
- **Files modified:** 3

## Accomplishments
- `Binding("o", "open_object", "Open")` and `Binding("space", "toggle_default", "Toggle")` added to ProjectDetail
- `action_open_object` validates highlighted_object, shows "No object selected" error if None, delegates to `_do_open` worker
- `_do_open` worker calls `open_object(item, config)` in thread, shows success toast via `_success_message`, shows "Failed to open: {value}" error toast on exception
- `action_toggle_default` flips `item.open_by_default`, calls `row.refresh_indicator()` to update dot immediately, delegates to `_save_toggle` worker
- `_save_toggle` worker calls `save_projects(self.app._projects)` to persist to TOML
- All `app.notify()` calls use `markup=False` (3 occurrences, T-03-02-01 mitigated)
- Both workers use `exit_on_error=False` (T-03-02-02 mitigated)
- 7 new TUI pilot tests (4 x `test_o_`, 2 x `test_space_`) and 1 store round-trip test (`test_toggle_round_trip`)
- Full suite: 87 tests pass

## Task Commits

1. **Task 1: Add o and space bindings to ProjectDetail with toast feedback** - `4f35363` (feat, TDD)

## Files Created/Modified
- `src/joy/widgets/project_detail.py` - Added `from textual import work` import, `_success_message`/`_truncate` imports, o and space BINDINGS, `action_open_object`, `_do_open`, `action_toggle_default`, `_save_toggle` methods
- `tests/test_tui.py` - Added `mock_operations` and `mock_save` fixtures, modified `_sample_projects` to set `open_by_default=False` on first object and add empty project, added 6 new pilot tests for ACT-01 and ACT-03
- `tests/test_store.py` - Added `test_toggle_round_trip` store-level integration test for ACT-03 persistence

## Decisions Made
- Lazy imports inside `@work` threads (`from joy.operations import open_object`) avoid module-level circular dependency risks and keep the worker self-contained
- `action_toggle_default` updates the dot indicator synchronously (main thread) before dispatching the background save -- ensures immediate visual feedback with no perceptible lag
- Split pattern `action_open_object` + `_do_open` cleanly separates the synchronous None-guard and error notification from the potentially-blocking subprocess call

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface Scan

T-03-02-01 (markup injection): Mitigated -- all 3 `app.notify()` calls in project_detail.py use `markup=False`.
T-03-02-02 (worker crash): Mitigated -- both `@work` decorators use `exit_on_error=False`.
T-03-02-03 (TOML tamper): Accepted -- single-user local tool, established atomic write pattern.
T-03-02-04 (subprocess elevation): Accepted -- mitigated upstream in Phase 1 (AppleScript escaping, array-form subprocess).

No new trust boundary surfaces introduced beyond those already in the threat register.

## Self-Check: PASSED

Files found:
- src/joy/widgets/project_detail.py: FOUND
- tests/test_tui.py: FOUND
- tests/test_store.py: FOUND
- .planning/phases/03-activation/03-02-SUMMARY.md: FOUND (this file)

Commits found:
- 4f35363: FOUND

Test suite: 87 passed, 1 deselected

---
*Phase: 03-activation*
*Completed: 2026-04-11*
