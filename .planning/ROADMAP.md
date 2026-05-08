# Roadmap: joy

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-12)
- ✅ **v1.1 Workspace Intelligence** — Phases 6-13 (shipped 2026-04-14)
- ✅ **v1.2 Cross-Pane Intelligence** — Phases 14-16 (shipped 2026-04-15)
- ✅ **v1.3 Unified Object View** — Phase 17 (shipped 2026-04-22)
- 🚧 **v1.4 Frontend Refactor & UI Polish** — Phases 18-21 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-5) — SHIPPED 2026-04-12</summary>

- [x] Phase 1: Foundation (3/3 plans) — completed 2026-04-10
- [x] Phase 2: TUI Shell (3/3 plans) — completed 2026-04-11
- [x] Phase 3: Activation (3/3 plans) — completed 2026-04-11
- [x] Phase 4: CRUD (3/3 plans) — completed 2026-04-11
- [x] Phase 5: Settings, Search & Distribution (3/3 plans) — completed 2026-04-12

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Workspace Intelligence (Phases 6-13) — SHIPPED 2026-04-14</summary>

- [x] Phase 6: Models, Config & Store (2/2 plans) — completed 2026-04-13
- [x] Phase 7: Git Worktree Discovery (2/2 plans) — completed 2026-04-13
- [x] Phase 8: 4-Pane Layout (2/2 plans) — completed 2026-04-13
- [x] Phase 9: Worktree Pane (3/3 plans) — completed 2026-04-13
- [x] Phase 10: Background Refresh Engine (2/2 plans) — completed 2026-04-13
- [x] Phase 11: MR & CI Status (3/3 plans) — completed 2026-04-13
- [x] Phase 12: iTerm2 Integration & Terminal Pane (3/3 plans) — completed 2026-04-14
- [x] Phase 13: Project Workflow, Settings & Docs (4/4 plans) — completed 2026-04-14

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Cross-Pane Intelligence (Phases 14-16) — SHIPPED 2026-04-15</summary>

- [x] Phase 14: Relationship Foundation & Badges (3/3 plans) — completed 2026-04-15
- [x] Phase 15: Cross-Pane Selection Sync (3/3 plans) — completed 2026-04-15
- [x] Phase 16: Live Data Propagation (2/2 plans) — completed 2026-04-15

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Unified Object View (Phase 17) — SHIPPED 2026-04-22</summary>

- [x] Phase 17: Fix iTerm2 Integration Bugs (3/3 plans) — completed 2026-04-16

Plus 21 quick tasks: unified detail view, DISPATCH table, icon ribbon, archive browser, new-project modal, cross-pane sync polish.

Full details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

### 🚧 v1.4 Frontend Refactor & UI Polish (In Progress)

**Milestone Goal:** Separate frontend from backend using Ports & Adapters architecture, establish a three-layer test strategy, and fix UI bugs/inconsistencies — making the codebase safe for future UI work.

- [x] **Phase 18: Contracts & Facades** - Define Protocol-based port interfaces and add public facade methods to all widgets (completed 2026-05-08)
- [x] **Phase 19: Service Extraction & Backend Tests** - Extract PaneCoordinator, DataOrchestrator, ProjectService from app.py with co-evolved backend tests (completed 2026-05-08)
- [x] **Phase 20: Widget Tests & Snapshots** - Widget-level tests with fake backend injection and snapshot baselines for key screens (completed 2026-05-08)
- [ ] **Phase 21: UI Polish** - Systematic audit and fix of visual inconsistencies across all panes

## Phase Details

### Phase 18: Contracts & Facades
**Goal**: All widget-to-backend boundaries have explicit Protocol contracts and public facade methods — no private field access crosses module boundaries
**Depends on**: Phase 17 (v1.3 complete)
**Requirements**: CNTR-01, CNTR-02, CNTR-03, CNTR-04, CNTR-05, ARCH-01
**Success Criteria** (what must be TRUE):
  1. A ports.py module exists defining StoragePort, GitDataPort, TerminalPort, and OpenerPort as typing.Protocol classes with typed method signatures
  2. SyncablePane Protocol exists defining sync_to() and clear_selection() contracts that WorktreePane and TerminalPane satisfy structurally
  3. app.py no longer accesses any widget private attributes (no _project, _rows, _cursor, _worktrees, _sessions references on widget instances)
  4. ProjectDetail, WorktreePane, and TerminalPane each expose documented public properties/methods for all data that app.py needs
  5. No widget imports any Protocol adapter directly — all dependency wiring flows through app.py as composition root
**Plans**: 3 plans
Plans:
- [x] 18-01-PLAN.md — Protocol contracts and widget facades
- [x] 18-02-PLAN.md — App and resolver facades
- [x] 18-03-PLAN.md — Replace private access and contract tests

### Phase 19: Service Extraction & Backend Tests
**Goal**: All cross-pane sync, background data loading, and project persistence logic lives in testable pure-Python services outside app.py — with backend tests proving correctness without any TUI dependency
**Depends on**: Phase 18
**Requirements**: SRVC-01, SRVC-02, SRVC-03, SRVC-04, SRVC-05, TEST-01, TEST-02, TEST-03, TEST-06, ARCH-02, ARCH-03
**Success Criteria** (what must be TRUE):
  1. PaneCoordinator handles all 6 sync directions and its logic is tested via plain pytest (no Textual app, no pilot) with assertions on which panes receive sync_to/clear_selection calls
  2. DataOrchestrator handles background data loading coordination (_worktrees_ready/_sessions_ready) and relationship computation, tested without TUI
  3. ProjectService handles project CRUD, archive/unarchive, MR auto-add propagation, and persistence — tested via plain pytest against real TOML files in a tmp directory
  4. app.py is under 400 lines of code and under 10 instance variables — it composes services and wires them to Textual lifecycle hooks
  5. All @work(thread=True) decorators remain on app.py methods; extracted services contain zero Textual imports
  6. The 10 previously-failing tests in test_propagation.py and test_sync.py pass (tech debt resolved)
  7. All existing tests pass after every individual service extraction (no big-bang migration)
**Plans**: 4 plans
Plans:
- [x] 19-01-PLAN.md — Extract PaneCoordinator (sync logic) + backend tests
- [x] 19-02-PLAN.md — Extract DataOrchestrator (data coordination) + backend tests
- [x] 19-03-PLAN.md — Extract ProjectService (CRUD/archive) + backend tests
- [x] 19-04-PLAN.md — Slim app.py to composition root + verify all constraints

### Phase 20: Widget Tests & Snapshots
**Goal**: Widget behavior is verified through Textual pilot tests using injected fake backends, and key screens have snapshot baselines for visual regression detection
**Depends on**: Phase 19
**Requirements**: TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. At least one widget test per pane (ProjectList, ProjectDetail, WorktreePane, TerminalPane) runs with FakeBackend adapters injected via constructor — no @patch mocking of internals
  2. Snapshot baselines exist for at least 3 key screens (initial render, project selected, sync active) captured via pytest-textual-snapshot
  3. Running `pytest --snapshot-update` regenerates baselines; `pytest` without the flag detects visual regressions
**Plans**: 3 plans
Plans:
- [x] 20-01-PLAN.md — Test infrastructure: pytest downgrade, pytest-textual-snapshot, FakeBackend adapters
- [x] 20-02-PLAN.md — Widget pilot tests for all four panes (TEST-04)
- [x] 20-03-PLAN.md — Snapshot baseline tests for key screens (TEST-05)

### Phase 21: UI Polish
**Goal**: All four panes render with consistent spacing, alignment, truncation, and focus indicators — visual bugs identified and fixed after architecture stabilization
**Depends on**: Phase 20
**Requirements**: UIPOL-01, UIPOL-02
**Success Criteria** (what must be TRUE):
  1. A documented audit checklist exists covering spacing, alignment, truncation, and focus indicators for all panes (ProjectList, ProjectDetail, WorktreePane, TerminalPane, MRPane)
  2. Every bug identified in the audit is fixed — no known visual inconsistencies remain across the five panes
  3. Focus indicators (border color, highlight styling) behave consistently when tabbing between panes
**Plans**: 2 plans
Plans:
- [x] 21-01-PLAN.md — Fix CSS inconsistencies across all 5 widget panes
- [ ] 21-02-PLAN.md — Remove app.py duplicate CSS, update snapshots, visual verification
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 18 → 19 → 20 → 21

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | ✓ Complete | 2026-04-10 |
| 2. TUI Shell | v1.0 | 3/3 | ✓ Complete | 2026-04-11 |
| 3. Activation | v1.0 | 3/3 | ✓ Complete | 2026-04-11 |
| 4. CRUD | v1.0 | 3/3 | ✓ Complete | 2026-04-11 |
| 5. Settings, Search & Distribution | v1.0 | 3/3 | ✓ Complete | 2026-04-12 |
| 6. Models, Config & Store | v1.1 | 2/2 | ✓ Complete | 2026-04-13 |
| 7. Git Worktree Discovery | v1.1 | 2/2 | ✓ Complete | 2026-04-13 |
| 8. 4-Pane Layout | v1.1 | 2/2 | ✓ Complete | 2026-04-13 |
| 9. Worktree Pane | v1.1 | 3/3 | ✓ Complete | 2026-04-13 |
| 10. Background Refresh Engine | v1.1 | 2/2 | ✓ Complete | 2026-04-13 |
| 11. MR & CI Status | v1.1 | 3/3 | ✓ Complete | 2026-04-13 |
| 12. iTerm2 Integration & Terminal Pane | v1.1 | 3/3 | ✓ Complete | 2026-04-14 |
| 13. Project Workflow, Settings & Docs | v1.1 | 4/4 | ✓ Complete | 2026-04-14 |
| 14. Relationship Foundation & Badges | v1.2 | 3/3 | ✓ Complete | 2026-04-15 |
| 15. Cross-Pane Selection Sync | v1.2 | 3/3 | ✓ Complete | 2026-04-15 |
| 16. Live Data Propagation | v1.2 | 2/2 | ✓ Complete | 2026-04-15 |
| 17. Fix iTerm2 Integration Bugs | v1.3 | 3/3 | ✓ Complete | 2026-04-16 |
| 18. Contracts & Facades | v1.4 | 3/3 | Complete    | 2026-05-08 |
| 19. Service Extraction & Backend Tests | v1.4 | 4/4 | Complete    | 2026-05-08 |
| 20. Widget Tests & Snapshots | v1.4 | 3/3 | Complete    | 2026-05-08 |
| 21. UI Polish | v1.4 | 1/2 | In Progress|  |
