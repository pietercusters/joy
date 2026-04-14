---
phase: 13-project-workflow-settings-docs
verified: 2026-04-14T12:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open joy, register a repo via Settings (s), then verify projects with a matching repo field appear under a named group header in the left pane"
    expected: "Projects with repo='<name>' grouped under '<name>' header; projects without a matching repo in 'Other' group (or flat list if no registered repos)"
    why_human: "Visual TUI grouping layout cannot be tested without a running app. The code wiring is complete but the visual grouping behavior needs end-to-end confirmation."
  - test: "In Settings modal (s), tab to the Repos section, press 'a', enter a valid directory path, press Enter"
    expected: "Repo is added with auto-detected remote_url and forge. Repo name derived from directory basename. 'Added repo: <name>' notification shown."
    why_human: "TUI interaction with PathInputModal, auto-detection from real git repo, and notification display require running app."
  - test: "In Settings modal, navigate to a repo row (j/k), press 'd', confirm removal in dialog"
    expected: "Repo removed from list. 'Removed repo: <name>' notification shown. Projects that referenced it now appear in 'Other' group."
    why_human: "Full delete flow with ConfirmationModal and subsequent project regrouping requires running app."
---

# Phase 13: Project Workflow, Settings & Docs Verification Report

**Phase Goal:** Users can manage repos from the settings UI, see projects grouped by repo, and find all prerequisites documented
**Verified:** 2026-04-14T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Projects pane groups projects under their associated repo with a section header | VERIFIED | `project_list.py:_rebuild()` groups by `p.repo` field into `grouped` dict, mounts `GroupHeader(repo_name)` before each group's `ProjectRow` widgets. Alphabetical sort confirmed (line 171). |
| 2 | Projects not matched to any repo appear in an "Other" group | VERIFIED | `_rebuild()` lines 163-185: projects with `repo=None` or unregistered repo go to `other` list; mounted with `GroupHeader("Other")` last when repo groups also exist. |
| 3 | README documents all prerequisites: gh CLI auth, glab CLI auth, iTerm2 Python API enabled, iTerm2 shell integration | VERIFIED | `README.md` lines 5-47: `## Prerequisites` section before `## Installation` (line 49). Contains "Enable Python API", `iterm2_shell_integration`, `gh auth login`, `glab auth login`. All 4 items present. |
| 4 | SettingsModal has a Repos section with j/k navigation, add (a) and remove (d) functionality, persisted via save_repos | VERIFIED | `settings.py` has `_RepoListWidget` (VerticalScroll, can_focus=True) with j/k/a/d bindings; `_add_repo()` validates path, auto-detects remote_url/forge, calls `save_repos()`; `_delete_repo()` uses ConfirmationModal and calls `save_repos()`. App reloads on both Save and Escape paths. |

**Score:** 4/4 truths verified

### Requirement Traceability Note

The requirement IDs in plan frontmatter (FLOW-01, FLOW-02, FLOW-03, DOC-01) are phase-scoped identifiers defined in ROADMAP.md and 13-CONTEXT.md, not entries in `REQUIREMENTS.md` (which tracks CORE-xx, PROJ-xx, SETT-xx, etc.). This is consistent across other phase plans in this codebase. The ROADMAP.md success criteria are the authoritative contract.

**FLOW-03** (new-project-from-worktree) was explicitly dropped by the user before planning began, confirmed in 13-CONTEXT.md and the roadmap strikethrough. No plans claim FLOW-03. No gap.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/models.py` | Project.repo field | VERIFIED | Line 78: `repo: str | None = None`. `to_dict()` conditionally includes it (line 87-88). |
| `src/joy/store.py` | Repo-aware serialization | VERIFIED | `_toml_to_projects()` line 93: `repo = proj_data.get("repo")`. `load_repos`, `save_repos`, `get_remote_url`, `validate_repo_path` all present. |
| `src/joy/app.py` | self._repos init + load + pass | VERIFIED | Line 62: `self._repos: list[Repo] = []`. `_load_data()` loads repos. `_set_projects` passes to ProjectList. `_reload_repos`/`_apply_repos` refresh on settings close. |
| `src/joy/widgets/project_list.py` | Refactored with VerticalScroll + GroupHeader + cursor | VERIFIED | Contains `_ProjectScroll`, `GroupHeader`, `ProjectRow`, `ProjectList(Widget, can_focus=True)`. No ListView/JoyListView. All cursor methods present. |
| `src/joy/screens/settings.py` | Extended SettingsModal with Repos section | VERIFIED | Contains `PathInputModal`, `_RepoRow`, `_RepoListWidget`, `_AddRepoRequest`, `_DeleteRepoRequest`. `SettingsModal.__init__` accepts `repos`. `_add_repo`, `_delete_repo` implemented. |
| `README.md` | Prerequisites section | VERIFIED | Lines 5-47: `## Prerequisites` with 4 subsections before `## Installation` (line 49). |
| `tests/test_models.py` | Tests for Project.repo field | VERIFIED | `test_project_repo_default_none`, `test_project_repo_set`, `test_project_to_dict_with_repo`, `test_project_to_dict_without_repo` all present. |
| `tests/test_store.py` | Round-trip tests for repo field | VERIFIED | `test_round_trip_project_with_repo`, `test_round_trip_project_without_repo`, `test_load_projects_missing_repo_field` all present. |
| `tests/test_screens.py` | Tests for repos section in SettingsModal | VERIFIED | `test_settings_repos_section_visible`, `test_settings_repos_list_shows_repos`, `test_settings_repos_empty_message`, `test_settings_save_still_returns_config_with_repos` all present. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `models.py` | `store.py` | `Project.to_dict()` / `_toml_to_projects()` | WIRED | `to_dict()` includes `repo` when set; `_toml_to_projects()` reads `proj_data.get("repo")` — backward compatible. |
| `project_list.py` | `app.py` | `set_projects(projects, repos)` | WIRED | `app._set_projects()` line 112 calls `set_projects(projects, self._repos)`. `action_new_project` line 321 also passes `self._repos`. |
| `project_list.py` | `models.py` | `project.repo` for grouping | WIRED | `_rebuild()` line 163: `if p.repo and p.repo in repo_names` — reads `Project.repo` for grouping. |
| `settings.py` | `store.py` | `save_repos`, `load_repos`, `get_remote_url`, `validate_repo_path` | WIRED | All four functions imported at module level (lines 14). Used in `_add_repo` and `_delete_repo`. |
| `settings.py` | `models.py` | `Repo`, `detect_forge` | WIRED | Imported line 13: `from joy.models import Config, PresetKind, Repo, detect_forge`. Used in `_add_repo`. |
| `app.py` | `settings.py` | `action_settings` passes `self._repos` | WIRED | Line 369: `self.push_screen(SettingsModal(self._config, self._repos), on_settings)`. |
| `app.py` | `project_list.py` | `_apply_repos` refreshes grouping | WIRED | Line 387: `self.query_one(ProjectList).set_projects(self._projects, self._repos)`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `project_list.py` | `self._projects`, `self._repos` | `app._set_projects` ← `load_projects()` / `load_repos()` from TOML | Yes — TOML files read via `tomllib.load()` | FLOWING |
| `settings.py` (`_RepoListWidget`) | `self._repos` | `SettingsModal.__init__` ← `app._repos` ← `load_repos()` | Yes — populated from real TOML data | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Python imports for all new classes | `python -c "from joy.widgets.project_list import ProjectList, ProjectRow, GroupHeader"` | OK | PASS |
| Python imports for settings | `python -c "from joy.screens.settings import SettingsModal, PathInputModal, _RepoListWidget"` | OK | PASS |
| Python imports for app | `python -c "from joy.app import JoyApp"` | OK | PASS |
| Model + store tests | `uv run pytest tests/test_models.py tests/test_store.py -q` | 70 passed | PASS |
| Settings screen tests | `uv run pytest tests/test_screens.py -k "settings" -q` | 8 passed | PASS |
| Full non-slow test suite | `uv run pytest tests/ -m "not slow" -q` | 272 passed, 0 failed | PASS |
| No JoyListView/ListView in project_list.py | `grep "JoyListView\|ListView" project_list.py` | no matches | PASS |
| Focus targets updated | `grep "project-listview" project_detail.py terminal_pane.py` | no matches | PASS |
| README Prerequisites before Installation | `grep -n "## Prerequisites\|## Installation" README.md` | Prereqs=line 5, Install=line 49 | PASS |
| All 4 prerequisite items in README | `grep -c "Enable Python API\|iterm2_shell_integration\|gh auth login\|glab auth login" README.md` | count=5 (gh auth login appears in glab section too) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FLOW-01 (phase-scoped) | 13-01, 13-02 | Project-repo association + grouped project list | SATISFIED | `Project.repo` field, TOML round-trip, ProjectList grouping all verified |
| FLOW-02 (phase-scoped) | 13-03 | Repo registry UI in SettingsModal | SATISFIED | SettingsModal Repos section with add/remove/navigate verified |
| FLOW-03 (phase-scoped) | (none) | New-project-from-worktree — explicitly dropped | N/A (dropped) | Confirmed dropped in ROADMAP.md (strikethrough) and 13-CONTEXT.md |
| DOC-01 (phase-scoped) | 13-04 | README Prerequisites section | SATISFIED | Prerequisites section verified at README.md lines 5-47 |

**REQUIREMENTS.md cross-reference:** FLOW-xx and DOC-xx IDs are phase-scoped and not present in REQUIREMENTS.md. REQUIREMENTS.md tracks v1/v2 system requirements (CORE-xx, PROJ-xx, etc.) — no phase-13 orphaned requirements found there.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `settings.py` | 36 | `placeholder=` in Input widget | Info | UI placeholder text for path input — expected behavior, not a stub |
| `project_list.py` | 271 | `placeholder=` in Input widget | Info | UI placeholder text for filter input — expected behavior, not a stub |

No blockers or warnings found. All `placeholder=` occurrences are legitimate UI placeholder text on Input widgets, not stub implementations.

### Human Verification Required

#### 1. Repo Grouping in Project Pane

**Test:** Register at least one repo via Settings (`s` key). Assign a project's `repo` field to match the registered repo name (via TOML editor or future project-edit flow). Relaunch or refresh joy.
**Expected:** The project list shows the project under a bold header matching the repo name. Other projects without a matching repo appear under "Other" (when mixed groups exist) or in a flat list (when no repos are registered).
**Why human:** Visual TUI rendering of group headers and project rows cannot be verified programmatically without running the app.

#### 2. Add Repo via Settings Modal

**Test:** Press `s`, tab to the `_RepoListWidget` (repo list section), press `a`. In the PathInputModal, type a valid git repo directory path (e.g., `/Users/<you>/Github/<project>`), press Enter.
**Expected:** Notification "Added repo: <name>" appears. The repo list updates to show the new entry. On modal close, the project list re-groups with the new repo.
**Why human:** Requires interactive TUI with actual filesystem path and git repo present for remote URL auto-detection.

#### 3. Remove Repo with Confirmation

**Test:** With at least one repo registered, tab to the repo list in Settings, navigate to a repo with `j`/`k`, press `d`. Confirm in the ConfirmationModal.
**Expected:** Repo removed from list. "Removed repo: <name>" notification. Projects that had that repo field now appear in "Other" on next view.
**Why human:** Requires interactive ConfirmationModal flow and visual verification that projects regroup correctly.

### Gaps Summary

No automated-detectable gaps found. All four phase success criteria are verified to be correctly implemented in the codebase:

1. **Projects pane grouping** — `_rebuild()` in `project_list.py` correctly groups by `Project.repo` with `GroupHeader` widgets.
2. **"Other" group** — Projects without matching repo go to `other` list; "Other" header shown only when mixed groups exist.
3. **Prerequisites documentation** — README has complete `## Prerequisites` section before `## Installation` with all 4 items.
4. **SettingsModal Repos section** — Full CRUD (add/delete) with j/k navigation, path validation, auto-detection, and independent persistence.

Three human verification items remain for visual/interactive TUI confirmation, which is expected for TUI phases.

---

_Verified: 2026-04-14T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
