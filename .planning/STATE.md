---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Frontend Refactor & UI Polish
status: requirements_defining
stopped_at: "Defining requirements for v1.4"
last_updated: "2026-05-07T00:00:00.000Z"
last_activity: 2026-05-07
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-07)

**Core value:** Every artifact for the active project, openable instantly from one keyboard-driven interface.
**Current focus:** v1.4 Frontend Refactor & UI Polish

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-07 — Milestone v1.4 started

Progress: ░░░░░░░░░░░░░░░░░░░░ 0% (0/0 phases)

## Milestone Summary

v1.4 Frontend Refactor & UI Polish:

- Separate frontend/backend using Ports & Adapters architecture
- Three-layer test strategy (backend/widget/snapshot)
- Extract PaneCoordinator, DataOrchestrator, ProjectService from app.py
- Widget facade methods replacing private field access
- Audit and fix UI bugs/inconsistencies
- Fix failing tests in test_propagation.py and test_sync.py

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

Key decisions from v1.3:

- Tab creation on explicit h-key only (auto-sync removed)
- clear_selection() replaces dimmed-state concept
- DISPATCH table per kind in dispatch.py (declarative keystroke routing)
- Virtual rows in ProjectDetail (REPO, TERMINALS, resolver worktrees) — no persistence mutation
- Session-scoped fixture for test isolation (autouse, patches 5 path constants)
- ArchivedProject wraps Project + archived_at; archive.toml uses keyed schema

### Roadmap Evolution

- v1.3 complete — Phase 17 + 21 quick tasks
- v1.4 started — Frontend Refactor & UI Polish

### Pending Todos

None.

### Blockers/Concerns

Known tech debt:
- test_propagation.py::TestTerminalAutoRemove (6 tests) — references non-existent JoyApp._propagate_terminal_auto_remove
- test_sync.py (4 tests) — terminal sync / resolver returns empty list for terminals

### Quick Tasks Completed

(None yet for v1.4)

## Session Continuity

Last session: 2026-05-07
Stopped at: Defining requirements for v1.4
Resume: Continue requirement definition → roadmap creation
