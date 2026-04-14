---
phase: 01-foundation
plan: 02
subsystem: database
tags: [toml, tomllib, tomli_w, persistence, atomic-write, dataclasses]

# Dependency graph
requires:
  - phase: 01-foundation plan 01
    provides: models.py with Project, ObjectItem, Config dataclasses and PresetKind enum

provides:
  - store.py with load_projects, save_projects, load_config, save_config
  - Atomic write pattern using tempfile.mkstemp + os.replace
  - Keyed TOML schema [projects.{name}] for human-editable project files
  - Auto-directory creation for ~/.joy/ on first write
  - Graceful missing-file defaults (empty list / default Config)

affects: [02-tui-shell, 03-activation, 04-crud, 05-settings]

# Tech tracking
tech-stack:
  added: [tomllib (stdlib 3.11+), tomli_w 1.x]
  patterns:
    - "Atomic write: tempfile.mkstemp(dir=same_fs) + os.replace (D-10)"
    - "Keyword-only path param with default for testability without touching real ~/.joy/"
    - "Keyed TOML schema [projects.{name}] with [[projects.{name}.objects]] array-of-tables (D-01, D-02)"

key-files:
  created:
    - src/joy/store.py
    - tests/test_store.py
  modified: []

key-decisions:
  - "Keyed TOML schema [projects.{name}] keeps projects human-editable and hand-renameable (D-01)"
  - "All store functions use keyword-only path param so tests pass tmp_path without touching real ~/.joy/"
  - "Atomic write uses mkstemp(dir=path.parent) to ensure temp is on same filesystem as target (required for os.replace)"

patterns-established:
  - "Atomic file write: tempfile.mkstemp + os.replace in _atomic_write helper"
  - "Test isolation: keyword-only path= param on all I/O functions, tests use tmp_path fixture"
  - "TOML round-trip: tomllib.load (read) + tomli_w.dumps (write) with date objects handled natively"

requirements-completed: [DIST-02, OBJ-01, OBJ-02, OBJ-03, OBJ-04, OBJ-05, OBJ-06, OBJ-07]

# Metrics
duration: 10min
completed: 2026-04-10
---

# Phase 1 Plan 02: TOML Persistence Layer Summary

**Atomic TOML persistence layer using tomllib/tomli_w with keyed [projects.{name}] schema, tempfile+os.replace atomic writes, and test-isolation via keyword-only path parameters**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-10T18:00:00Z
- **Completed:** 2026-04-10T18:10:07Z
- **Tasks:** 1 (TDD: test RED commit + implementation GREEN commit)
- **Files modified:** 2

## Accomplishments

- Implemented store.py with load/save for both projects and config using the keyed TOML schema from D-01/D-02
- Established atomic write pattern (tempfile.mkstemp on same filesystem + os.replace) preventing partial writes per D-10
- All 10 store tests pass; full test suite (45 tests) passes with no regressions

## Task Commits

Each task was committed atomically:

1. **TDD RED - Failing store tests** - `a46bcae` (test)
2. **TDD GREEN - store.py implementation** - `91e3247` (feat)

## Files Created/Modified

- `src/joy/store.py` - TOML persistence layer with load_projects, save_projects, load_config, save_config, and _atomic_write helper
- `tests/test_store.py` - 10 unit tests covering round-trips, keyed schema, atomic write, missing files, and field preservation

## Decisions Made

None beyond plan spec - followed plan exactly. Key implementation details:
- `tempfile.mkstemp(dir=path.parent)` ensures temp file is on same filesystem as target (required for atomic `os.replace`)
- `_toml_to_projects` handles `created` field as either a `date` object (from tomllib) or missing (falls back to today)
- Store does not import `ObjectType` directly - works through `PresetKind` values and lets models handle the mapping

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation worked on first attempt. All 10 tests passed immediately after writing store.py.

## Self-Check

Files created:
- `src/joy/store.py` exists: FOUND
- `tests/test_store.py` exists: FOUND

Commits:
- `a46bcae` (test - failing store tests): FOUND
- `91e3247` (feat - store.py implementation): FOUND

## Self-Check: PASSED

## Known Stubs

None - store.py is fully wired with no placeholder data. All functions perform real I/O.

## Next Phase Readiness

- Phase 2 (TUI Shell) can `from joy.store import load_projects, load_config` immediately
- Phase 3 (Activation) reads Config via store, passes it to operations.py per D-11
- Phase 4 (CRUD) uses save_projects to persist changes after add/edit/delete operations
- No blockers

---
*Phase: 01-foundation*
*Completed: 2026-04-10*
