# Roadmap: joy

## Overview

joy delivers a keyboard-driven Python TUI for managing coding project artifacts. The roadmap progresses from a headless data layer (proven models, persistence, and operations) through a read-only TUI shell, then wires in activation operations (the core value), adds full CRUD via modals, and finishes with settings, search/filter, reordering, and distribution packaging. Each phase delivers a complete, testable capability that the next phase builds on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Data model, TOML persistence, and all object-type operations (no UI)
- [ ] **Phase 2: TUI Shell** - Two-pane layout, navigation, project/object display (read-only, no mutations)
- [ ] **Phase 3: Activation** - Wire o/O/space operations into the TUI to deliver the core value proposition
- [ ] **Phase 4: CRUD** - Add, edit, delete objects and projects via modal forms
- [ ] **Phase 5: Settings, Search & Distribution** - Settings screen, project filtering, object reordering, packaging

## Phase Details

### Phase 1: Foundation
**Goal**: A fully tested headless layer that can load/save projects from TOML, define all object types and presets, and perform every type-specific operation (clipboard, browser, IDE, Obsidian, iTerm2) via subprocess
**Depends on**: Nothing (first phase)
**Requirements**: OBJ-01, OBJ-02, OBJ-03, OBJ-04, OBJ-05, OBJ-06, OBJ-07, PRESET-01, PRESET-02, PRESET-03, PRESET-04, PRESET-05, PRESET-06, PRESET-07, PRESET-08, PRESET-09, DIST-02
**Success Criteria** (what must be TRUE):
  1. A Project with ObjectItems can be created in Python, serialized to TOML, and deserialized back with no data loss
  2. Every object type operation works when called directly: string copies to clipboard, url opens browser, Notion/Slack urls open desktop apps, obsidian opens via URI scheme, file opens in editor, worktree opens in IDE, agents creates/focuses iTerm2 window
  3. The preset-to-type mapping is complete: all nine preset kinds (mr, branch, ticket, thread, file, note, worktree, agents, url) resolve to the correct operation
  4. Data files are written atomically (temp file + os.replace) so interrupted writes cannot corrupt ~/.joy/projects.toml
  5. All operations and persistence have passing unit tests
**Plans**: TBD

### Phase 2: TUI Shell
**Goal**: Users see a two-pane Textual app with project list on the left and object detail on the right, can navigate with keyboard, and see icons, key hints, and focus indicators -- but cannot mutate anything yet
**Depends on**: Phase 1
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-06, CORE-07, PROJ-01, PROJ-02, PROJ-03
**Success Criteria** (what must be TRUE):
  1. App launches and shows a two-pane layout: project list (left) with selection highlighting, project detail (right) showing objects with Nerd Font icons
  2. User can navigate the project list with j/k or arrow keys; selecting a project immediately updates the detail pane
  3. First project is auto-selected on startup so the detail pane is never empty
  4. Footer displays context-sensitive keyboard hints that update when focus changes between panes
  5. Pressing Escape always navigates back with no focus traps; app starts in under 350ms to first paint
**Plans**: TBD
**UI hint**: yes

### Phase 3: Activation
**Goal**: Users can open any object with `o`, open all "open by default" objects with `O`, and toggle the default set with space -- delivering the core value of instant artifact access
**Depends on**: Phase 2
**Requirements**: ACT-01, ACT-02, ACT-03, ACT-04, CORE-05
**Success Criteria** (what must be TRUE):
  1. Pressing `o` on a selected object performs its type-specific operation (opens URL, copies string, launches IDE, etc.) without freezing the TUI
  2. Pressing `O` activates all objects marked "open by default" for the current project, in display order
  3. Pressing `space` toggles an object's "open by default" status and the change persists across app restarts
  4. Each object displays a visible indicator (filled/empty) showing its "open by default" status
  5. Status bar shows immediate feedback after every activation ("Copied to clipboard", "Opened in browser")
**Plans**: TBD
**UI hint**: yes

### Phase 4: CRUD
**Goal**: Users can create new projects, add/edit/delete objects, and delete projects -- all through modal forms with keyboard navigation and confirmation dialogs
**Depends on**: Phase 3
**Requirements**: PROJ-04, PROJ-05, MGMT-01, MGMT-02, MGMT-03
**Success Criteria** (what must be TRUE):
  1. User can create a new project by entering a name and it appears in the project list with pre-defined object slots
  2. User can add an object to a project by pressing `a`, choosing a preset or generic type, and entering a value
  3. User can edit a selected object by pressing `e`, modifying its value in a form, and seeing the change reflected immediately
  4. User can delete a selected object by pressing `d` with a confirmation prompt
  5. User can delete a project by pressing the delete key with a confirmation prompt; deletion removes it from the list and selects an adjacent project
**Plans**: TBD
**UI hint**: yes

### Phase 5: Settings, Search & Distribution
**Goal**: Users can configure global preferences via a settings screen, filter projects by name, reorder objects to control activation sequence, and install joy globally via uv
**Depends on**: Phase 4
**Requirements**: SETT-01, SETT-02, SETT-03, SETT-04, SETT-05, SETT-06, PROJ-06, MGMT-04, DIST-01, DIST-03, DIST-04
**Success Criteria** (what must be TRUE):
  1. A dedicated settings screen is accessible from the main screen where user can view and edit IDE, editor, vault path, terminal tool, and default "open by default" object types
  2. User can press `/` to filter the project list by substring in real-time; clearing the filter restores the full list
  3. User can press `J`/`K` to move the selected object up/down, changing display order which controls `O` activation order; reorder persists across restarts
  4. App is installable globally via `uv tool install git+<repo>` and `joy --version` outputs the installed version
  5. README documents installation, first-run setup, and key usage
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/? | Not started | - |
| 2. TUI Shell | 0/? | Not started | - |
| 3. Activation | 0/? | Not started | - |
| 4. CRUD | 0/? | Not started | - |
| 5. Settings, Search & Distribution | 0/? | Not started | - |
