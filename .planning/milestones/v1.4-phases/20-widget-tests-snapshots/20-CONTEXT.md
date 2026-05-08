# Phase 20: Widget Tests & Snapshots - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Widget behavior is verified through Textual pilot tests using injected fake backends, and key screens have snapshot baselines for visual regression detection

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Protocol contracts in `ports.py`: StoragePort, GitDataPort, TerminalPort, OpenerPort, SyncablePane
- Existing conftest.py with session-scoped store path isolation fixture
- Existing test files for many modules (test_project_list.py, test_worktree_pane.py, test_terminal_pane.py, test_mr_pane.py, etc.)

### Established Patterns
- Session-scoped autouse fixture for store isolation (patches joy.store paths)
- Models in `joy.models`: Project, Config, Repo, WorktreeInfo, TerminalSession, ObjectItem
- Widgets accept backend ports via constructor (Phase 18/19 architecture)

### Integration Points
- Widgets: ProjectList, ProjectDetail, WorktreePane, TerminalPane, MRPane (all in src/joy/widgets/)
- Services: project_service.py, data_orchestrator.py, pane_coordinator.py
- App: app.py (JoyApp) — the main Textual application

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
