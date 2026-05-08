---
phase: 19-service-extraction-backend-tests
plan: 02
status: complete
started: 2026-05-08
completed: 2026-05-08
---

# Plan 19-02 Summary: DataOrchestrator Extraction

## What was built
Extracted DataOrchestrator service from app.py handling data loading coordination, relationship computation, MR auto-add propagation, stale tab healing, and worktree link computation. Pure Python, zero Textual imports.

## Key files

### Created
- `src/joy/data_orchestrator.py` — DataOrchestrator with 9 methods
- `tests/test_data_orchestrator.py` — 21 backend tests across 5 test classes

### Modified
- `src/joy/app.py` — Delegates to orchestrator, removed 7 instance vars (-82 lines)
- `tests/test_propagation.py` — Updated _PropContext for new delegation pattern

## Deviations
- Updated existing test_propagation.py _PropContext to include _orchestrator since _propagate_mr_auto_add now delegates.

## Self-Check: PASSED
- 444 tests pass (423 existing + 21 new)
- Zero `self._rel_index`, `self._worktrees_ready`, `self._sessions_ready` in app.py
- Zero Textual imports in data_orchestrator.py
- app.py: 1026 -> 944 lines
