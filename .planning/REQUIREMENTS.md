# Requirements: joy

**Defined:** 2026-04-10
**Core Value:** Every artifact for the active project, openable instantly from one keyboard-driven interface.

## v1.1 Requirements

Requirements for the Workspace Intelligence milestone.

### REPO — Repo Registry

- [ ] **REPO-01**: User can add a repo to the registry with local path and optional remote URL via settings
- [ ] **REPO-02**: User can remove a repo from the registry
- [ ] **REPO-03**: User can edit a repo entry (local path, remote URL)
- [ ] **REPO-04**: App auto-deduces remote URL from `git remote get-url origin` when local path is entered
- [ ] **REPO-05**: App auto-detects forge type (GitHub vs GitLab) from remote URL pattern
- [ ] **REPO-06**: App validates that local path exists when saving a repo entry

### PANE — Layout

- [ ] **PANE-01**: App shows a 2x2 pane layout (projects top-left, details top-right, terminal bottom-left, worktrees bottom-right)
- [ ] **PANE-02**: User can cycle focus between all panes via Tab

### WKTR — Worktree Pane

- [ ] **WKTR-01**: Worktree pane auto-discovers all active git worktrees from registered repos
- [ ] **WKTR-02**: Worktrees are grouped by repo with section headers; repos with no active worktrees are hidden
- [ ] **WKTR-03**: Each worktree row shows branch name and status indicators on line 1, abbreviated path on line 2
- [ ] **WKTR-04**: Dirty indicator shown when worktree has uncommitted changes
- [ ] **WKTR-05**: No-remote indicator shown when branch has no upstream tracking branch
- [ ] **WKTR-06**: Worktrees on branches matching configured filter patterns are hidden from the pane
- [ ] **WKTR-07**: Open MR/PR number and status badge shown per worktree row when available
- [ ] **WKTR-08**: CI pipeline status (pass/fail/pending) shown per worktree row when available
- [ ] **WKTR-09**: MR author and last commit (short hash + message) shown on second line of worktree row
- [ ] **WKTR-10**: Worktree pane is read-only — no selection or interaction

### TERM — Terminal Pane

- [ ] **TERM-01**: Terminal pane lists all active iTerm2 sessions
- [ ] **TERM-02**: Claude agent sessions grouped at top; other sessions grouped below
- [ ] **TERM-03**: Each session row shows session name, foreground process, and working directory
- [ ] **TERM-04**: Claude sessions show a busy/waiting indicator based on foreground process state
- [ ] **TERM-05**: User can navigate sessions with j/k and press Enter to focus that iTerm2 window
- [ ] **TERM-06**: Pane shows a graceful "unavailable" state when iTerm2 Python API is inaccessible

### REFR — Background Refresh

- [ ] **REFR-01**: App refreshes worktree and terminal data at a configurable interval (default 30s)
- [ ] **REFR-02**: User can trigger an immediate refresh with `r` key from any pane
- [ ] **REFR-03**: Last refresh timestamp shown in the UI at all times
- [ ] **REFR-04**: When refresh fails, panes show stale data with age indicator rather than blanking
- [ ] **REFR-05**: Background refresh does not reset cursor position in any pane

### SETT — New Settings

- [ ] **SETT-07**: Setting for background refresh interval (integer seconds, default 30)
- [ ] **SETT-08**: Setting for branch filter patterns (comma-separated list, default "main,testing")

### FLOW — Project Workflow

- [ ] **FLOW-01**: Projects pane groups projects under their associated repo with a header
- [ ] **FLOW-02**: Projects not matched to any repo appear in an "Other" group
- [ ] **FLOW-03**: User can create a new project from a discovered worktree (pre-fills name, branch object, MR URL)

### DOC — Documentation

- [ ] **DOC-01**: README documents all prerequisites: `gh` CLI auth, `glab` CLI auth, iTerm2 Python API enabled, iTerm2 shell integration

## v1.0 Requirements (Complete — shipped 2026-04-12)

### Core TUI

- ✓ **CORE-01**: App shows a two-pane layout — project list (left) + project detail (right)
- ✓ **CORE-02**: User can navigate with j/k or arrow keys throughout
- ✓ **CORE-03**: Footer shows context-sensitive keyboard hints that update when focus changes
- ✓ **CORE-04**: Pressing Escape always navigates back; no focus traps
- ✓ **CORE-05**: Status bar shows immediate feedback after every action
- ✓ **CORE-06**: App starts in under 350ms to first paint
- ✓ **CORE-07**: Each object type displays a Nerd Font icon for fast visual scanning

### Projects

- ✓ **PROJ-01**: Project list visible on left pane with clear selection highlighting
- ✓ **PROJ-02**: First project auto-selected on startup
- ✓ **PROJ-03**: Navigating project list immediately updates detail pane
- ✓ **PROJ-04**: User can create a new project
- ✓ **PROJ-05**: User can delete a project after confirming
- ✓ **PROJ-06**: User can filter project list via `/` (real-time substring)

### Object Types

- ✓ **OBJ-01**: `string` type — copies value to clipboard
- ✓ **OBJ-02**: `url` type — opens in default browser
- ✓ **OBJ-03**: `url` type (Notion/Slack) — opens in desktop app
- ✓ **OBJ-04**: `obsidian` type — opens via `obsidian://` URI
- ✓ **OBJ-05**: `file` type — opens in configured editor
- ✓ **OBJ-06**: `git worktree` type — opens in configured IDE
- ✓ **OBJ-07**: `special string` type — creates/focuses named iTerm2 window via AppleScript

### Pre-defined Objects

- ✓ **PRESET-01 through PRESET-09**: All 9 preset kinds (mr, branch, ticket, thread, file, note, worktree, agents, url)

### Activation

- ✓ **ACT-01**: `o` activates selected object
- ✓ **ACT-02**: `O` activates all open-by-default objects
- ✓ **ACT-03**: `space` toggles open-by-default status
- ✓ **ACT-04**: Visual indicator for open-by-default status

### Object Management

- ✓ **MGMT-01**: `a` opens add-object form
- ✓ **MGMT-02**: `e` opens edit form
- ✓ **MGMT-03**: `d` removes object after confirming
- ✓ **MGMT-04**: Deferred (object reordering)

### Settings

- ✓ **SETT-01 through SETT-06**: IDE, editor, Obsidian vault, terminal, default open kinds, settings screen

### Distribution

- ✓ **DIST-01 through DIST-04**: uv install, ~/.joy/ data, README, --version flag

## v2 Requirements

### Convenience

- **CONV-01**: Quick-add from clipboard — detect URL or branch name, pre-fill add form
- **CONV-02**: Configurable keybinding overrides

### Platform

- **PLAT-01**: Linux support (once macOS-specific integrations are abstracted)

### Extensibility

- **EXT-01**: External plugin/extension API for custom object types

### Collaboration

- **COLLAB-01**: Multi-vault Obsidian support

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mouse interaction | Keyboard-driven identity; two paradigms dilute UX |
| Undo/redo | Confirmation dialogs suffice for joy's simple mutations |
| Animations / transitions | Anti-pattern in terminals per TUI design research |
| Cloud sync | User can git-track `~/.joy/`; adds network + auth complexity |
| Cross-platform (v1) | macOS-only; uses iTerm2, app URL schemes, AppleScript |
| Plugin API (v1) | Single-user tool; add types by editing code |
| Multi-vault Obsidian (v1) | Single configured vault is sufficient |
| Configurable keybindings (v1) | Ship opinionated defaults; premature complexity |
| Inline editing | Known TUI anti-pattern; use modal overlays |
| Auto-discovery of repos on disk | Too broad (finds unwanted repos), user manages registry manually |
| Interactive worktree creation/deletion | Not in scope; joy is a viewer, not a git manager |
| Ahead/behind remote count | Excluded by design; requires git fetch, adds network ops |

## Traceability

*Populated by roadmapper during roadmap creation.*

| Requirement | Phase | Status |
|-------------|-------|--------|
| REPO-01 | — | Pending |
| REPO-02 | — | Pending |
| REPO-03 | — | Pending |
| REPO-04 | — | Pending |
| REPO-05 | — | Pending |
| REPO-06 | — | Pending |
| PANE-01 | — | Pending |
| PANE-02 | — | Pending |
| WKTR-01 | — | Pending |
| WKTR-02 | — | Pending |
| WKTR-03 | — | Pending |
| WKTR-04 | — | Pending |
| WKTR-05 | — | Pending |
| WKTR-06 | — | Pending |
| WKTR-07 | — | Pending |
| WKTR-08 | — | Pending |
| WKTR-09 | — | Pending |
| WKTR-10 | — | Pending |
| TERM-01 | — | Pending |
| TERM-02 | — | Pending |
| TERM-03 | — | Pending |
| TERM-04 | — | Pending |
| TERM-05 | — | Pending |
| TERM-06 | — | Pending |
| REFR-01 | — | Pending |
| REFR-02 | — | Pending |
| REFR-03 | — | Pending |
| REFR-04 | — | Pending |
| REFR-05 | — | Pending |
| SETT-07 | — | Pending |
| SETT-08 | — | Pending |
| FLOW-01 | — | Pending |
| FLOW-02 | — | Pending |
| FLOW-03 | — | Pending |
| DOC-01 | — | Pending |

**Coverage:**
- v1.1 requirements: 35 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 35

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-13 after v1.1 milestone start*
