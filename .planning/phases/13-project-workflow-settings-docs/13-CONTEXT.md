# Phase 13: Project Workflow, Settings & Docs - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Repo registry management in the settings UI, project grouping by repo in the projects pane, and README prerequisite documentation. Users can register repos, see their projects organized under repo headers, and find setup prerequisites in the README.

Out of scope: new-project-from-worktree (FLOW-03, explicitly dropped), any changes to WorktreePane, TerminalPane, or MR/CI status (Phases 9–12 features unchanged).

</domain>

<decisions>
## Implementation Decisions

### Project-Repo Association
- **D-01:** Add `repo: str | None` to the `Project` dataclass. Field stores `Repo.name` (a plain string). Existing TOML entries without `repo` deserialize as `None` — backward compatible.
- **D-02:** Projects with `repo = None`, or with a `repo` value that doesn't match any registered `Repo.name`, appear in the "Other" group. No error, no warning — same silent-skip contract as Phase 7 D-02.

### Repo Registry UI
- **D-03:** Extend the existing `SettingsModal` (`s` key) with a Repos section appended below the current settings fields. No new modal, no new keybinding — single configuration entry point.
- **D-04:** Repos section shows a scrollable list of registered repos. Each row: repo name + local path. Navigation with j/k within the list.
- **D-05:** `a` (in repos section) adds a new repo via a simple path-input modal — user enters a local path. App calls `get_remote_url(local_path)` to fill `remote_url`, calls `detect_forge(remote_url)` to set `forge`, and derives repo `name` from `os.path.basename(local_path)`. Uses Phase 6 `validate_repo_path()` before saving. All three auto-detection functions already exist in `store.py` / `models.py`.
- **D-06:** `d` (in repos section) removes the selected repo after confirmation — reuses `ConfirmationModal`.
- **D-07:** On repo removal, projects that had `repo` pointing to that repo retain their `repo` field value unchanged (they fall into "Other" group until re-linked or the repo is re-added).

### Project Pane Grouping
- **D-08:** Refactor `ProjectList` from `ListView`-based to `VerticalScroll` + `GroupHeader(Static)` + project row widgets — same architectural pattern as `WorktreePane` and `TerminalPane`.
- **D-09:** Project grouping order: alphabetical by repo name, "Other" last. Within each group: preserve original project order (as loaded from TOML). `GroupHeader` rows are not navigable (not in `_rows`). Repos with no projects are omitted (same as Phase 9 D-10: no empty group headers).
- **D-10:** Navigation: cursor-based pattern — `_cursor: int`, `_rows: list[ProjectRow]`, `--highlight` CSS class on the focused row. `j`/`down` = cursor down, `k`/`up` = cursor up, `Enter` = select. Replicate the `ProjectDetail` / `TerminalPane` cursor pattern exactly.
- **D-11:** Filter mode (`/`): filter hides non-matching project rows. If a group has no matching projects after filtering, its `GroupHeader` is also hidden. Filter Input mounted above the `VerticalScroll` container (same position as before). Escape restores the full grouped view from the canonical `app._projects` list.
- **D-12:** `set_projects(projects: list[Project])` remains the sole public API on `ProjectList`. Internally, `set_projects` reads `app._repos` (or receives repos as a second argument) to build the grouped layout. The caller (JoyApp) does not need to know about grouping — same sole-API pattern as `set_worktrees()`.

### Documentation
- **D-13:** Update the existing README. Add a "Prerequisites" section before "Installation" documenting (in order): (1) iTerm2 with Python API enabled (Preferences → General → Magic), (2) iTerm2 shell integration installed (`curl -L iterm2.com/shell_integration/zsh | zsh`), (3) `gh` CLI installed + `gh auth login` completed, (4) `glab` CLI installed + `glab auth login` completed (for GitLab repos).

### Claude's Discretion
- Exact widget class name for project rows in the refactored pane (e.g., `ProjectRow(Static)` or similar).
- Whether `set_projects` receives repos as a second argument or reads them via `self.app._repos` — choose what's cleaner given the existing `_set_projects` / `_load_data` flow in `app.py`.
- Visual style of repo GroupHeader in the projects pane (can match WorktreePane's header style exactly or have minor variation — lean toward consistency).
- Exact SettingsModal layout for the repos section (vertical list vs simple label rows).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` §"Phase 13: Project Workflow, Settings & Docs" — Goal, requirements FLOW-01, FLOW-02, DOC-01, success criteria (items 1, 2, 4 — item 3 dropped)
- `.planning/PROJECT.md` — Core value, snappy/minimal constraint, macOS-only platform

### Prior phases this phase builds on
- `.planning/phases/09-worktree-pane/09-CONTEXT.md` — D-06 (VerticalScroll + GroupHeader + Static rows), D-09 (GroupHeader CSS), D-10 (empty group omission), D-03 (`set_worktrees()` sole-API pattern → replicate as `set_projects()`)
- `.planning/phases/12-iterm2-integration-terminal-pane/12-CONTEXT.md` — D-11 (cursor/`_rows`/`--highlight` navigation pattern, same to replicate for ProjectList)
- `.planning/phases/06-models-config-store/` — Phase 6 implemented `get_remote_url`, `validate_repo_path`, `detect_forge`, and repo store CRUD (`add_repo`, `remove_repo`) — all ready to use

### Existing code this phase modifies
- `src/joy/models.py` — Add `repo: str | None = None` to `Project` dataclass; update `Project.to_dict()` to serialize it
- `src/joy/widgets/project_list.py` — Full refactor from ListView to VerticalScroll + GroupHeader + cursor-based navigation
- `src/joy/screens/settings.py` — Extend `SettingsModal` with Repos section (list + add/delete)
- `src/joy/app.py` — `_set_projects()`: pass repos to `ProjectList.set_projects()` or ensure `_repos` is accessible; `_load_data()`: also load repos alongside projects
- `README.md` — Add "Prerequisites" section before "Installation"

### Existing code to reuse (read before implementing)
- `src/joy/widgets/project_detail.py` — `GroupHeader(Static)` class (lines ~50–61), `_cursor`/`_rows`/`--highlight`/`action_cursor_up/down` pattern (lines ~103–179) — replicate for ProjectList
- `src/joy/widgets/worktree_pane.py` — `set_worktrees()` sole-API pattern, GroupHeader usage
- `src/joy/screens/confirmation.py` — `ConfirmationModal` for repo delete confirmation
- `src/joy/store.py` — `load_repos()`, `add_repo()`, `remove_repo()`, `get_remote_url()`, `validate_repo_path()` (Phase 6 implementations)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GroupHeader(Static)` from `src/joy/widgets/project_detail.py:50-61` — import and reuse directly in refactored `project_list.py`.
- `ProjectDetail._cursor` / `_rows` / `--highlight` / `action_cursor_up/down` pattern (`project_detail.py:103-179`) — replicate verbatim for the new cursor-based `ProjectList`.
- `WorktreePane.set_worktrees()` sole-API pattern — replicate as `ProjectList.set_projects(projects, repos)` or `set_projects(projects)` with internal repo access.
- `ConfirmationModal` (`src/joy/screens/confirmation.py`) — reuse for repo delete confirmation in SettingsModal.
- `ValueInputModal` (`src/joy/screens/value_input.py`) — or a new `PathInputModal` for the "add repo" local path input.
- `store.py`: `get_remote_url(local_path)`, `validate_repo_path(local_path)`, `detect_forge(remote_url)`, `add_repo()`, `remove_repo()` — all Phase 6 deliverables, ready to wire into the UI.

### Established Patterns
- `Project` currently has no `repo` field — D-01 adds `repo: str | None = None` with a default so TOML backward compatibility is maintained via `dataclasses.field(default=None)`.
- `SettingsModal` returns `Config | None` — the extended modal must still return `Config | None`; repo changes persist separately via `save_repos()`.
- Filter mode in `project_list.py` uses `on_input_changed` + `set_projects()` — this pattern carries over to the refactored widget, filtering the grouped data rather than a flat list.

### Integration Points
- `JoyApp._load_data()` currently loads projects + config. Phase 13 extends it to also call `load_repos()` and store in `self._repos`.
- `JoyApp._set_projects()` passes projects to `ProjectList.set_projects()` — extend to also pass repos for grouping.
- `SettingsModal` currently receives `Config` and returns `Config | None`. Repo section changes call `save_repos()` independently (repos live in config.toml's `[repos]` section, separate from the `[settings]` key loaded by `Config`).

</code_context>

<specifics>
## Specific Ideas

- FLOW-03 (new-project-from-worktree) explicitly dropped by user — do not implement, do not reference in plans.
- GroupHeader styling in the projects pane should match WorktreePane exactly for visual consistency.
- Filter mode: group headers disappear with their group when filtering leaves a group empty — same behavior as how repos with no worktrees are hidden in WorktreePane.

</specifics>

<deferred>
## Deferred Ideas

- **FLOW-03: New-project-from-worktree** — Explicitly removed from Phase 13 scope by user. Not deferred to a future phase — dropped entirely for now.

</deferred>

---

*Phase: 13-project-workflow-settings-docs*
*Context gathered: 2026-04-14*
