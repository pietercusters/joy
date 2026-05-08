---
phase: 19-service-extraction-backend-tests
plan: 03
status: complete
started: 2026-05-08
completed: 2026-05-08
---

# Plan 19-03 Summary: ProjectService Extraction

## What was built
Extracted ProjectService from app.py handling project CRUD, duplicate validation, archival, and add-object logic. Pure Python, zero Textual imports.

## Key files

### Created
- `src/joy/project_service.py` — ProjectService with 8 methods
- `tests/test_project_service.py` — 15 backend tests

### Modified
- `src/joy/app.py` — Delegates project ops to _project_svc, removed _projects ivar
- `tests/test_propagation.py` — Updated _PropContext for ProjectService

## Self-Check: PASSED
- 459 tests pass (444 + 15 new)
- Zero Textual imports in project_service.py
- Zero `self._projects` in app.py (all via _project_svc.projects)
