# Roadmap: joy

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-12)
- ✅ **v1.1 Workspace Intelligence** — Phases 6-13 (shipped 2026-04-14)
- 🚧 **v1.2 Cross-Pane Intelligence** — Phases 14-16 (in progress)

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

### 🚧 v1.2 Cross-Pane Intelligence (In Progress)

**Milestone Goal:** Connect the four panes through a shared relationship model so selecting any item syncs related items across panes, and live refresh automatically propagates changes to project data.

- [ ] **Phase 14: Relationship Foundation & Badges** — Resolver computes cross-pane relationships; cursor preservation survives DOM rebuilds; badge counts prove the index works
- [ ] **Phase 15: Cross-Pane Selection Sync** — Selecting any item in any pane syncs cursors across all other panes, with keyboard toggle
- [ ] **Phase 16: Live Data Propagation** — Background refresh auto-propagates worktree/MR/agent changes to project data

## Phase Details

### Phase 14: Relationship Foundation & Badges
**Goal**: Users see accurate worktree and agent counts on every project row, proving the cross-pane relationship model works end-to-end
**Depends on**: Phase 13
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, BADGE-01, BADGE-02, BADGE-03
**Success Criteria** (what must be TRUE):
  1. Each project row displays the correct count of active worktrees belonging to that project (matching by repo + branch/path)
  2. Each project row displays the correct count of active agent sessions belonging to that project (matching by session name)
  3. Badge counts update automatically after each background refresh cycle without user intervention
  4. Switching between projects or triggering a refresh does not cause the WorktreePane or TerminalPane cursor to jump to row 0 — cursors stay on the same worktree/session they were on before the rebuild
**Plans**: 3 plans

Plans:
- [ ] 14-01-PLAN.md — Relationship resolver: compute_relationships() and RelationshipIndex (TDD)
- [ ] 14-02-PLAN.md — Cursor identity preservation: WorktreePane and TerminalPane (parallel with 14-01)
- [ ] 14-03-PLAN.md — Badge wiring: ProjectRow counts, app orchestration, human verify

### Phase 15: Cross-Pane Selection Sync
**Goal**: Users can navigate any pane and see all other panes automatically track to related items, with a toggle to turn sync on or off
**Depends on**: Phase 14
**Requirements**: SYNC-01, SYNC-02, SYNC-03, SYNC-04, SYNC-05, SYNC-06, SYNC-07, SYNC-08, SYNC-09
**Success Criteria** (what must be TRUE):
  1. Selecting a project moves the WorktreePane cursor to a related worktree and the TerminalPane cursor to a related agent session (or keeps current position if no match)
  2. Selecting a worktree moves the ProjectList cursor to its owning project and the TerminalPane cursor to a related agent (or keeps current if no match)
  3. Selecting an agent session moves the ProjectList cursor to its owning project and the WorktreePane cursor to a related worktree (or keeps current if no match)
  4. Focus always remains on the pane the user is actively navigating — synced panes update their cursor silently without stealing focus
  5. User can toggle sync on/off via a keyboard shortcut and the current sync state is visible in the footer key hints
**Plans**: TBD

Plans:
- [ ] 15-01: TBD
- [ ] 15-02: TBD

### Phase 16: Live Data Propagation
**Goal**: Background refresh automatically keeps project objects in sync with live worktree, MR, and agent state — adding, removing, and moving objects without user action
**Depends on**: Phase 15
**Requirements**: PROP-01, PROP-02, PROP-03, PROP-04, PROP-05, PROP-06, PROP-07, PROP-08
**Success Criteria** (what must be TRUE):
  1. When a worktree disappears from git for 2+ consecutive refreshes, its object is silently removed from the project; when an MR is detected for a project's branch and no MR object exists, it is silently auto-added
  2. When a worktree's branch matches a different project (same repo), the worktree object moves to that project automatically — branch objects are never touched by propagation
  3. When an agent session disappears from iTerm2, its project object is visually dimmed (stale); when the session reappears, the stale marker clears
  4. MR objects are auto-added but never auto-removed by propagation; branch objects are never modified by propagation
  5. Projects without a registered repo are completely excluded from all propagation — their objects are never touched
**Plans**: TBD

Plans:
- [ ] 16-01: TBD
- [ ] 16-02: TBD

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
| 14. Relationship Foundation & Badges | v1.2 | 0/? | Not started | - |
| 15. Cross-Pane Selection Sync | v1.2 | 0/? | Not started | - |
| 16. Live Data Propagation | v1.2 | 0/? | Not started | - |
