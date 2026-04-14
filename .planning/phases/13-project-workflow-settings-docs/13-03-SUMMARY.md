---
phase: 13-project-workflow-settings-docs
plan: 03
subsystem: screens
tags: [settings, repos, modal, tui, crud]

# Dependency graph
requires:
  - "13-01 (Project.repo field, Repo model, store functions)"
provides:
  - "SettingsModal Repos section with add/remove/navigate"
  - "PathInputModal for repo path entry"
  - "App reloads repos and refreshes project grouping after settings close"
affects: [13-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inner widget messaging: _RepoListWidget posts _AddRepoRequest/_DeleteRepoRequest to parent SettingsModal"
    - "Lazy import for ConfirmationModal inside _delete_repo to avoid circular deps"
    - "Repo changes persisted immediately via save_repos, independent of Config save flow"

key-files:
  created: []
  modified:
    - src/joy/screens/settings.py
    - src/joy/app.py
    - tests/test_screens.py

key-decisions:
  - "PathInputModal defined in settings.py (not a separate file) — single-use modal for repo path entry"
  - "_RepoListWidget uses message posting to communicate with parent SettingsModal — clean separation"
  - "Repos saved immediately on add/remove, not deferred to Save button — independent from Config flow"
  - "App reloads repos on both Save and Escape from settings modal — repos may change without saving config"

patterns-established:
  - "VerticalScroll with can_focus=True for focusable sub-lists inside modals"
  - "Message-based parent-child communication for widget actions in modals"

requirements-completed: [FLOW-02]

# Metrics
duration: 4min
completed: 2026-04-14
---

# Phase 13 Plan 03: SettingsModal Repos Section Summary

**Extended SettingsModal with a Repos section featuring j/k cursor navigation, path-validated add via PathInputModal, and confirmation-gated remove with independent persistence via save_repos**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-14T11:08:58Z
- **Completed:** 2026-04-14T11:12:55Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- Added `PathInputModal` for repo path entry with empty-string validation
- Added `_RepoRow(Static)` and `_RepoListWidget(VerticalScroll)` with j/k/a/d keybindings
- Extended `SettingsModal.__init__` to accept `repos: list[Repo] | None = None`
- Added Repos section to compose() with instructions label and focusable list widget
- Implemented `_add_repo()`: validates path via `validate_repo_path`, auto-detects remote URL and forge, checks for duplicate names, persists via `save_repos()`
- Implemented `_delete_repo()`: uses `ConfirmationModal` for confirmation, persists removal via `save_repos()`
- Updated `app.py` `action_settings()` to pass `self._repos` to SettingsModal
- Added `_reload_repos()` and `_apply_repos()` methods to refresh project grouping and worktrees after settings close
- App reloads repos on both Save and Escape paths (repos changes are independent of config save)
- Added 4 new tests: repos section visible, list shows repos, empty message, save regression
- All 262 existing tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Repos section to SettingsModal with add/remove functionality** - `7d68eb7`

## Files Created/Modified
- `src/joy/screens/settings.py` - Added PathInputModal, _RepoRow, _AddRepoRequest, _DeleteRepoRequest, _RepoListWidget; extended SettingsModal with repos param, compose section, add/delete methods
- `src/joy/app.py` - Updated action_settings to pass repos and reload on close; added _reload_repos and _apply_repos methods
- `tests/test_screens.py` - Added 4 new tests for repos section; updated existing save test for new tab count

## Decisions Made
- PathInputModal defined inline in settings.py rather than a separate file -- it is single-use and closely tied to the SettingsModal
- _RepoListWidget posts Messages to SettingsModal rather than using callbacks -- cleaner widget separation following Textual patterns
- Repos saved immediately on add/remove, not deferred to the Save Settings button -- repo changes are independent of Config changes
- App reloads repos on both Save and Escape -- user may add/remove repos then cancel config changes

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface
- Path input validated via `validate_repo_path()` (checks `Path.is_dir()`) per T-13-03
- `get_remote_url()` uses list-form subprocess (no shell injection)
- No new network endpoints or auth paths introduced

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SettingsModal now fully supports repo management alongside config editing
- Repos are persisted independently via save_repos()
- App refreshes project grouping and worktree discovery after settings close
- All tests pass

## Self-Check: PASSED
