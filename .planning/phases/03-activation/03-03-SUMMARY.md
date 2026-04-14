---
phase: 03-activation
plan: 03
subsystem: ui
tags: [textual, keybinding, bulk-open, worker, toast, priority-binding]

# Dependency graph
requires:
  - phase: 03-activation/03-01
    provides: _success_message helper, _truncate helper, ObjectRow dot indicator
  - phase: 03-activation/03-02
    provides: open_object integration, GROUP_ORDER, ProjectDetail._project
  - phase: 02-tui-shell
    provides: JoyApp, _load_data worker pattern, _config class attribute
provides:
  - JoyApp BINDINGS entry for O (shift+o,O with priority=True)
  - action_open_all_defaults collecting defaults in GROUP_ORDER order
  - _open_defaults background worker with continue-on-error and per-object toasts
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Binding('shift+o,O', ..., priority=True) for global keybindings that must fire from any focused widget"
    - "Comma-separated key string in Binding() expands to two entries in BindingsMap.key_to_bindings"
    - "priority=True on App-level Binding makes footer render the binding regardless of focused widget"
    - "exit_on_error=False on @work(thread=True) prevents worker exception from crashing the TUI"
    - "continue-on-error loop: collect errors list, show toasts after full iteration"

key-files:
  created: []
  modified:
    - src/joy/app.py
    - tests/test_tui.py

key-decisions:
  - "Used Binding('shift+o,O', ..., priority=True) instead of plain tuple ('O', ...) -- comma notation registers both key names so it works in real terminal (shift+o) and in Textual pilot tests (O)"
  - "priority=True required for two reasons: (1) fires action before focused child widget consumes the key, (2) causes Footer to render the binding label regardless of which widget has focus"
  - "Sequential open in background thread (not concurrent) to limit subprocess resource pressure per T-03-03-03 threat model acceptance"
  - "markup=False on all app.notify() calls to prevent Rich markup injection from user-supplied object values (T-03-03-02 mitigation)"

patterns-established:
  - "App-level global bindings in Textual 8.x: always use Binding(..., priority=True) with comma key notation for real-terminal + test compatibility"

requirements-completed: [ACT-02]

# Metrics
duration: 30min
completed: 2026-04-11
---

# Phase 03 Plan 03: O Global Binding with Sequential Bulk Open Summary

**JoyApp gains Binding("shift+o,O", priority=True) wired to action_open_all_defaults, opening all open_by_default objects sequentially per GROUP_ORDER with continue-on-error toasts from any pane**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-11
- **Completed:** 2026-04-11
- **Tasks:** 1 (+ fix)
- **Files modified:** 2

## Accomplishments

- `action_open_all_defaults` collects defaults in GROUP_ORDER display order and delegates to `_open_defaults` worker
- `_open_defaults` worker runs in a background thread (`exit_on_error=False`), opens objects sequentially, shows one success toast per object via `_success_message`, accumulates failures and shows one error toast per failure at the end
- Silent no-op when no default objects exist or project not yet loaded (D-11)
- `Binding("shift+o,O", "open_all_defaults", "Open All", priority=True)` fires globally regardless of focused widget, and renders in footer from both panes
- 3 new pilot tests (test_O_opens_default_objects, test_O_silent_noop_no_defaults, test_O_works_from_project_list); full suite 90 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: O global binding with sequential bulk open** - `282369c` (feat, TDD)
2. **Fix: priority shift+o,O binding for real terminal + footer visibility** - `c24ed8c` (fix)

## Files Created/Modified

- `src/joy/app.py` - Added `Binding` import, `Binding("shift+o,O", ..., priority=True)` entry in BINDINGS, `action_open_all_defaults` method, `_open_defaults` background worker
- `tests/test_tui.py` - Added 3 pilot tests for ACT-02 bulk open; updated `_sample_projects` so project-alpha has 2 open_by_default objects

## Decisions Made

- `Binding("shift+o,O", ..., priority=True)` rather than `("O", ...)` tuple — comma key notation required because Textual's real-terminal driver generates `"shift+o"` for Shift+O, but `pilot.press("O")` sends key `"O"`. The comma form expands to two `BindingsMap` entries covering both paths. `priority=True` is required for both global firing and footer rendering.
- Sequential execution in `_open_defaults` (not `asyncio.gather`) to limit concurrent subprocess spawning per T-03-03-03 threat acceptance
- `exit_on_error=False` on worker so a single subprocess failure does not crash the TUI (T-03-03-01 mitigation)
- All `app.notify()` calls use `markup=False` to prevent Rich markup injection from user-supplied object values (T-03-03-02 mitigation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed O binding not firing and not showing in footer**

- **Found during:** Visual verification after Task 1
- **Issue:** Original `("O", "open_all_defaults", "Open All")` tuple binding stored key `"O"` in BindingsMap. Real terminal sends `"shift+o"` for Shift+O — no match. Without `priority=True`, app-level binding also did not render in footer when a child widget had focus.
- **Fix:** Replaced tuple with `Binding("shift+o,O", "open_all_defaults", "Open All", priority=True)`. Comma notation registers both `"shift+o"` and `"O"` as separate BindingsMap entries. `priority=True` ensures both global firing and footer rendering.
- **Files modified:** `src/joy/app.py`
- **Commit:** `c24ed8c`

## Issues Encountered

None beyond the binding fix above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 03 is complete: dot indicators (Plan 01), o/space bindings (Plan 02), O bulk open (Plan 03)
- Pattern established: `Binding("shift+x,X", ..., priority=True)` for any future global app-level bindings

## Self-Check: PASSED

Files found: src/joy/app.py, tests/test_tui.py
Commits found: 282369c (original Task 1), c24ed8c (binding fix)
Tests: 90 passed

---
*Phase: 03-activation*
*Completed: 2026-04-11*
