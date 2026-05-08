---
phase: 20-widget-tests-snapshots
plan: 01
subsystem: testing
tags: [pytest, pytest-textual-snapshot, syrupy, fake-backend, protocol-conformance]

# Dependency graph
requires:
  - phase: 18-contracts-facades
    provides: Protocol contracts (StoragePort, GitDataPort, TerminalPort, OpenerPort)
provides:
  - pytest 8.4.x with pytest-textual-snapshot for snapshot testing
  - FakeBackend adapter classes (FakeStorage, FakeGitData, FakeTerminal, FakeOpener)
  - conftest fixtures with runtime Protocol conformance checks
  - snapshot marker excluding snapshot tests from default pytest runs
affects: [20-02-widget-tests, 20-03-snapshot-baselines]

# Tech tracking
tech-stack:
  added: [pytest-textual-snapshot 1.1.0, syrupy 4.8.0]
  patterns: [FakeBackend structural Protocol conformance, fixture-level isinstance checks]

key-files:
  created: [tests/fakes.py]
  modified: [pyproject.toml, tests/conftest.py]

key-decisions:
  - "Downgraded pytest from >=9.0.3 to >=8.4,<9 for syrupy 4.8.0 compatibility"
  - "FakeBackend classes use structural subtyping -- no import from joy.ports in fakes.py"
  - "Each conftest fixture asserts isinstance against its Protocol at creation time"

patterns-established:
  - "FakeBackend pattern: test doubles in tests/fakes.py conforming to ports.py Protocols via duck typing"
  - "Protocol conformance assertion: assert isinstance(fake, XxxPort) in fixture body"

requirements-completed: [TEST-04, TEST-05]

# Metrics
duration: 3min
completed: 2026-05-08
---

# Phase 20 Plan 01: Test Infrastructure Setup Summary

**Downgraded pytest to 8.4.x, installed pytest-textual-snapshot, created 4 FakeBackend adapters with Protocol conformance fixtures**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-08T11:43:21Z
- **Completed:** 2026-05-08T11:46:48Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Downgraded pytest from 9.0.3 to 8.4.2 to enable pytest-textual-snapshot (syrupy 4.8.0 requires pytest <9)
- Created tests/fakes.py with 4 FakeBackend adapter classes (FakeStorage, FakeGitData, FakeTerminal, FakeOpener) conforming to Protocol contracts via structural subtyping
- Extended tests/conftest.py with 4 fixtures including runtime isinstance Protocol checks
- Added snapshot marker to pytest config, excluded from default runs alongside slow and macos_integration
- All 459 existing tests pass unchanged (1 pre-existing failure in test_refresh.py is known tech debt)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update pyproject.toml and install dependencies** - `5d9f367` (chore)
2. **Task 2: Create FakeBackend adapters and conftest fixtures** - `0765f86` (feat)

## Files Created/Modified
- `pyproject.toml` - Downgraded pytest to >=8.4,<9, added pytest-textual-snapshot>=1.1.0, added snapshot marker
- `tests/fakes.py` - 4 FakeBackend adapter classes (FakeStorage, FakeGitData, FakeTerminal, FakeOpener) with structural Protocol conformance
- `tests/conftest.py` - 4 new fixtures (fake_storage, fake_terminal, fake_git_data, fake_opener) with isinstance Protocol assertions

## Decisions Made
- Downgraded pytest from >=9.0.3 to >=8.4,<9 -- required for syrupy 4.8.0 compatibility (transitive dep of pytest-textual-snapshot). pytest 8.4.2 passes all existing tests.
- FakeBackend classes use structural subtyping (duck typing) -- no import from joy.ports in fakes.py, conformance verified at fixture level via isinstance checks.
- Each conftest fixture asserts isinstance(fake, XxxPort) at creation time, catching Protocol drift early.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- FakeBackend adapters ready for widget behavior tests in Plan 02
- pytest-textual-snapshot installed and importable for snapshot baseline tests in Plan 03
- Snapshot marker configured so snapshot tests are excluded from default pytest runs

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 20-widget-tests-snapshots*
*Completed: 2026-05-08*
