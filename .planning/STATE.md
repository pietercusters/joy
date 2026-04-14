---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Cross-Pane Intelligence
status: defining_requirements
stopped_at: Milestone v1.2 started
last_updated: "2026-04-14T00:00:00.000Z"
last_activity: 2026-04-14
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Every artifact for the active project, openable instantly from one keyboard-driven interface.
**Current focus:** Defining requirements for v1.2 Cross-Pane Intelligence

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-14 — Milestone v1.2 started

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.MD Key Decisions table.

Key decisions carried from v1.1:
- list-form subprocess for all external calls (security)
- cursor/_rows/--highlight pattern for all scrollable panes
- lazy import + catch-all for iTerm2 graceful fallback
- pytest.mark.slow for TUI/integration tests

Key decisions for v1.2:
- Branch is king: branch objects on a project never change automatically
- MR and Worktree objects follow the branch (auto-add/remove/move)
- Agents are marked stale (not deleted) when session disappears
- Projects without a repo field are excluded from live sync
- main branch is protected; all work on feature branch, single PR at milestone end

### Pending Todos

None.

### Blockers/Concerns

None.
