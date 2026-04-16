# Roadmap: joy

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-12)
- ✅ **v1.1 Workspace Intelligence** — Phases 6-13 (shipped 2026-04-14)
- ✅ **v1.2 Cross-Pane Intelligence** — Phases 14-16 (shipped 2026-04-15)

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

## Progress

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

### Phase 17: Fix iTerm2 integration bugs from quick-260416-of2: remove auto-sync, close whole Tab on delete/archive, fix test isolation for ~/.joy/

**Goal:** Remove automatic iTerm2 tab creation (tabs only via h-key), close entire tab on project delete/archive, isolate all tests from real ~/.joy/ paths
**Requirements**: FIX17-REMOVE-AUTO-SYNC, FIX17-TAB-CLOSE-ON-DELETE-ARCHIVE, FIX17-TEST-ISOLATION, FIX17-CLOSE-TAB
**Depends on:** Phase 16
**Plans:** 2/2 plans complete

Plans:
- [x] 17-01-PLAN.md -- Test isolation fixture + close_tab function
- [x] 17-02-PLAN.md -- Remove auto-sync, tab-level close on delete/archive, remove ArchiveModal
