---
phase: 13-project-workflow-settings-docs
plan: 01
subsystem: models
tags: [dataclass, toml, serialization, backward-compat]

# Dependency graph
requires: []
provides:
  - "Project.repo field (str | None) for project-repo association"
  - "TOML round-trip for repo field with backward compatibility"
  - "JoyApp._repos: list[Repo] = [] initialization for downstream plans"
affects: [13-02, 13-03, 13-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conditional dict inclusion: only serialize optional fields when not None"
    - "Backward-compat TOML: use .get() with None default for new optional fields"

key-files:
  created: []
  modified:
    - src/joy/models.py
    - src/joy/store.py
    - src/joy/app.py
    - tests/test_models.py
    - tests/test_store.py

key-decisions:
  - "repo field omitted from to_dict() when None — keeps TOML clean for projects without repos"
  - "self._repos initialized as empty list in __init__ — safe default for Wave 2 plans"

patterns-established:
  - "Optional field serialization: omit from dict when None, include when set"

requirements-completed: [FLOW-01]

# Metrics
duration: 20min
completed: 2026-04-14
---

# Phase 13 Plan 01: Project.repo Field and JoyApp._repos Init Summary

**Added Project.repo optional field with backward-compatible TOML serialization and initialized JoyApp._repos for downstream Wave 2 plans**

## Performance

- **Duration:** 20 min
- **Started:** 2026-04-14T10:07:57Z
- **Completed:** 2026-04-14T10:27:35Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `repo: str | None = None` to Project dataclass with conditional serialization
- Wired repo field through TOML round-trip in store.py with full backward compatibility
- Initialized `self._repos: list[Repo] = []` on JoyApp for safe downstream access
- Added 7 new tests (4 model + 3 store) covering repo field behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Add repo field to Project and wire TOML round-trip** (TDD)
   - `d2fcd1b` (test: add failing tests for Project.repo field — RED)
   - `6887293` (feat: add Project.repo field with TOML round-trip — GREEN)
2. **Task 2: Initialize self._repos on JoyApp** - `34e4ab7` (feat)

## Files Created/Modified
- `src/joy/models.py` - Added `repo: str | None = None` to Project, updated `to_dict()` to conditionally include repo
- `src/joy/store.py` - Updated `_toml_to_projects()` to read repo field with `.get("repo")` fallback
- `src/joy/app.py` - Added `Repo` import and `self._repos: list[Repo] = []` in `JoyApp.__init__`
- `tests/test_models.py` - 4 new tests: repo default, repo set, to_dict with/without repo
- `tests/test_store.py` - 3 new tests: round-trip with repo, without repo, missing field backward compat

## Decisions Made
- repo field omitted from `to_dict()` when `None` to keep TOML files clean for existing projects without repos
- `self._repos` initialized in `__init__` (not `on_mount`) so it exists immediately for any downstream code path

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Project.repo field ready for use by Plan 13-02 (settings modal repo management) and 13-03 (project pane grouping)
- JoyApp._repos safely initialized — Wave 2 plans can reference it without AttributeError
- All 268 existing tests pass with no regressions

## Self-Check: PASSED

- All 6 files verified present
- All 3 commits verified in git log
- Key content patterns confirmed in models.py, store.py, app.py

---
*Phase: 13-project-workflow-settings-docs*
*Completed: 2026-04-14*
