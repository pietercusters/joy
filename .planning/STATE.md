---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Frontend Refactor & UI Polish
status: ready_to_plan
stopped_at: "Roadmap created, ready to plan Phase 18"
last_updated: "2026-05-07T00:00:00.000Z"
last_activity: 2026-05-07
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-07)

**Core value:** Every artifact for the active project, openable instantly from one keyboard-driven interface.
**Current focus:** Phase 18 — Contracts & Facades

## Current Position

Phase: 18 of 21 (Contracts & Facades) — first of 4 phases in v1.4
Plan: —
Status: Ready to plan
Last activity: 2026-05-07 — Roadmap created for v1.4

Progress: ░░░░░░░░░░░░░░░░░░░░ 0% (0/4 phases)

## Milestone Summary

v1.4 Frontend Refactor & UI Polish (4 phases, 21 requirements):

- Phase 18: Contracts & Facades (6 reqs) — Protocol ports + widget facade methods
- Phase 19: Service Extraction & Backend Tests (11 reqs) — core refactoring + backend tests + tech debt
- Phase 20: Widget Tests & Snapshots (2 reqs) — fake backend injection + snapshot baselines
- Phase 21: UI Polish (2 reqs) — visual audit + bug fixes

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Key decisions from v1.3:

- Tab creation on explicit h-key only (auto-sync removed)
- clear_selection() replaces dimmed-state concept
- DISPATCH table per kind in dispatch.py (declarative keystroke routing)
- Virtual rows in ProjectDetail (REPO, TERMINALS, resolver worktrees) — no persistence mutation
- Session-scoped fixture for test isolation (autouse, patches 5 path constants)

### Pending Todos

None.

### Blockers/Concerns

Known tech debt (targeted in Phase 19, TEST-06):
- test_propagation.py::TestTerminalAutoRemove (6 tests) — references non-existent JoyApp._propagate_terminal_auto_remove
- test_sync.py (4 tests) — terminal sync / resolver returns empty list for terminals

## Session Continuity

Last session: 2026-05-07
Stopped at: Roadmap created for v1.4 (4 phases, 21 requirements)
Resume: `/gsd-plan-phase 18` to plan Contracts & Facades
