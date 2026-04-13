# Roadmap: joy

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-12)
- 🚧 **v1.1 Workspace Intelligence** — Phases 6-13 (in progress)

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

### 🚧 v1.1 Workspace Intelligence (In Progress)

**Milestone Goal:** Transform joy from a static artifact launcher into a real-time workspace dashboard with live git, MR, and terminal state visible at a glance.

- [x] **Phase 6: Models, Config & Store** — Data models, config schema extensions, and TOML persistence for repos
- [ ] **Phase 7: Git Worktree Discovery** — Pure-logic module for discovering worktrees, dirty checks, and remote tracking
- [ ] **Phase 8: 4-Pane Layout** — Restructure from 2-pane to 2x2 grid with stub panes and Tab focus cycling
- [ ] **Phase 9: Worktree Pane** — Full worktree display with two-line rows, grouping by repo, and status indicators
- [x] **Phase 10: Background Refresh Engine** — Polling loop, manual refresh, timestamp display, and cursor preservation (completed 2026-04-13)
- [ ] **Phase 11: MR & CI Status** — GitHub/GitLab CLI integration for PR/MR status and CI pipeline indicators
- [ ] **Phase 12: iTerm2 Integration & Terminal Pane** — iTerm2 Python API connection, session enumeration, Claude detection, and terminal pane UI
- [ ] **Phase 13: Project Workflow, Settings & Docs** — Repo registry UI, project grouping by repo, new-project-from-worktree, README updates

## Phase Details

### Phase 6: Models, Config & Store
**Goal**: All data structures and persistence for the repo registry, worktree state, terminal sessions, and new settings exist and round-trip through TOML
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: REPO-01, REPO-02, REPO-03, REPO-04, REPO-05, REPO-06, SETT-07, SETT-08
**Success Criteria** (what must be TRUE):
  1. User can add, edit, and remove repos in config.toml and the data persists across app restarts
  2. App auto-deduces remote URL from local path via `git remote get-url origin` when adding a repo
  3. App auto-detects forge type (GitHub vs GitLab) from remote URL
  4. App validates that a repo's local path exists before saving
  5. Config.toml supports refresh_interval and branch_filter settings that survive round-trip read/write
**Plans:** 2 plans
Plans:
- [x] 06-01-PLAN.md — Repo model, detect_forge, Config extension (models.py + tests)
- [x] 06-02-PLAN.md — Repo store CRUD, get_remote_url, validate_repo_path (store.py + tests)

### Phase 7: Git Worktree Discovery
**Goal**: A standalone module can discover all active worktrees for registered repos with dirty and remote-tracking status, handling all git edge cases
**Depends on**: Phase 6
**Requirements**: WKTR-01, WKTR-04, WKTR-05, WKTR-06
**Success Criteria** (what must be TRUE):
  1. Given a list of registered repos, the module returns all active worktrees with branch name and path
  2. Each worktree reports whether it has uncommitted changes (dirty indicator)
  3. Each worktree reports whether its branch has an upstream tracking branch (no-remote indicator)
  4. Worktrees on branches matching configured filter patterns are excluded from results
**Plans:** 2 plans
Plans:
- [x] 07-01-PLAN.md — WorktreeInfo dataclass in models.py with unit tests
- [x] 07-02-PLAN.md — discover_worktrees function via TDD (worktrees.py + tests)

### Phase 8: 4-Pane Layout
**Goal**: The app displays a 2x2 grid layout with all four panes visible and focus cycling works across them, without breaking any existing functionality
**Depends on**: Phase 7
**Requirements**: PANE-01, PANE-02
**Success Criteria** (what must be TRUE):
  1. App shows four panes in a 2x2 grid: projects (top-left), details (top-right), terminal placeholder (bottom-left), worktree placeholder (bottom-right)
  2. User can cycle focus between all four panes using Tab
  3. All existing project list, detail pane, and keyboard navigation functionality works identically to v1.0
**Plans:** 2 plans
Plans:
- [x] 08-01-PLAN.md — Stub widgets (TerminalPane, WorktreePane) + failing TDD tests for 4-pane layout
- [x] 08-02-PLAN.md — Grid layout refactor in app.py + regression verification
**UI hint**: yes

### Phase 9: Worktree Pane
**Goal**: Users see a live, grouped list of all worktrees across registered repos with branch names, status indicators, and paths — at a glance without interaction
**Depends on**: Phase 8
**Requirements**: WKTR-02, WKTR-03, WKTR-10
**Success Criteria** (what must be TRUE):
  1. Worktrees are grouped under repo section headers; repos with no active worktrees are hidden
  2. Each worktree row shows branch name and dirty/no-remote indicators on line 1, abbreviated path on line 2
  3. Worktree pane is read-only — no selection cursor, no keyboard interaction beyond scrolling
**Plans:** 3 plans
Plans:
- [x] 09-01-PLAN.md — Wave 0 test scaffolding (test_worktree_pane.py with all unit + integration tests)
- [x] 09-02-PLAN.md — WorktreePane implementation + app-level data loading worker
- [x] 09-03-PLAN.md — Visual verification checkpoint (human-verify)
**UI hint**: yes

### Phase 10: Background Refresh Engine
**Goal**: Worktree data refreshes automatically on a timer without freezing the UI, and users can force-refresh and see when data was last updated
**Depends on**: Phase 9
**Requirements**: REFR-01, REFR-02, REFR-03, REFR-04, REFR-05
**Success Criteria** (what must be TRUE):
  1. Worktree data auto-refreshes at the configured interval (default 30s) without UI freezes
  2. User can press `r` from any pane to trigger an immediate refresh
  3. A last-refresh timestamp is visible in the UI at all times
  4. When a refresh fails, panes show stale data with an age indicator rather than going blank
  5. Background refresh does not reset cursor position in any pane
**Plans:** 2/2 plans complete
Plans:
- [x] 10-01-PLAN.md — Scroll preservation + border_title refresh label API on WorktreePane
- [x] 10-02-PLAN.md — Timer, r binding, timestamp push, and stale detection in JoyApp

### Phase 11: MR & CI Status
**Goal**: Users see open MR/PR status and CI pipeline results per worktree row, auto-detected from GitHub or GitLab
**Depends on**: Phase 10
**Requirements**: WKTR-07, WKTR-08, WKTR-09
**Success Criteria** (what must be TRUE):
  1. Worktree rows show open MR/PR number and status badge when a merge request exists for that branch
  2. Worktree rows show CI pipeline status (pass/fail/pending) when available
  3. MR author and last commit (short hash + message) shown on second line of worktree row when MR data is available
**Plans:** 3 plans
Plans:
- [ ] 11-01-PLAN.md — MRInfo dataclass + mr_status.py fetch module (TDD: GitHub/GitLab CLI integration)
- [ ] 11-02-PLAN.md — WorktreeRow MR rendering + WorktreePane wiring + app.py integration (TDD)
- [ ] 11-03-PLAN.md — Visual verification checkpoint (human-verify)
**UI hint**: yes

### Phase 12: iTerm2 Integration & Terminal Pane
**Goal**: Users see all active iTerm2 sessions in the terminal pane with Claude agent detection, and can focus any session with Enter
**Depends on**: Phase 10
**Requirements**: TERM-01, TERM-02, TERM-03, TERM-04, TERM-05, TERM-06
**Success Criteria** (what must be TRUE):
  1. Terminal pane lists all active iTerm2 sessions with session name, foreground process, and working directory
  2. Claude agent sessions are grouped at the top with a busy/waiting indicator
  3. User can navigate sessions with j/k and press Enter to focus that iTerm2 window
  4. When iTerm2 Python API is inaccessible, the pane shows a graceful "unavailable" message instead of crashing
**Plans**: TBD
**UI hint**: yes

### Phase 13: Project Workflow, Settings & Docs
**Goal**: Users can manage repos from the settings UI, see projects grouped by repo, create projects from discovered worktrees, and find all prerequisites documented
**Depends on**: Phase 11, Phase 12
**Requirements**: FLOW-01, FLOW-02, FLOW-03, DOC-01
**Success Criteria** (what must be TRUE):
  1. Projects pane groups projects under their associated repo with a section header
  2. Projects not matched to any repo appear in an "Other" group
  3. User can create a new project from a discovered worktree, with name, branch, and MR URL pre-filled
  4. README documents all prerequisites: gh CLI auth, glab CLI auth, iTerm2 Python API enabled, iTerm2 shell integration
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12 -> 13
(Phases 11 and 12 can execute in parallel; Phase 13 depends on both.)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | ✓ Complete | 2026-04-10 |
| 2. TUI Shell | v1.0 | 3/3 | ✓ Complete | 2026-04-11 |
| 3. Activation | v1.0 | 3/3 | ✓ Complete | 2026-04-11 |
| 4. CRUD | v1.0 | 3/3 | ✓ Complete | 2026-04-11 |
| 5. Settings, Search & Distribution | v1.0 | 3/3 | ✓ Complete | 2026-04-12 |
| 6. Models, Config & Store | v1.1 | 2/2 | ✓ Complete | 2026-04-13 |
| 7. Git Worktree Discovery | v1.1 | 0/2 | Planning complete | - |
| 8. 4-Pane Layout | v1.1 | 0/2 | Planning complete | - |
| 9. Worktree Pane | v1.1 | 0/3 | Planning complete | - |
| 10. Background Refresh Engine | v1.1 | 2/2 | Complete   | 2026-04-13 |
| 11. MR & CI Status | v1.1 | 0/3 | Planning complete | - |
| 12. iTerm2 Integration & Terminal Pane | v1.1 | 0/0 | Not started | - |
| 13. Project Workflow, Settings & Docs | v1.1 | 0/0 | Not started | - |
