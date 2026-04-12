---
phase: 05-settings-search-distribution
plan: 03
subsystem: ui
tags: [cli, version-flag, importlib-metadata, readme, documentation, distribution]

# Dependency graph
requires:
  - phase: 05-01
    provides: "Settings modal, filter mode, modified app.py main() structure"
provides:
  - "--version CLI flag using importlib.metadata with PackageNotFoundError fallback"
  - "_get_version() helper shared by main() and JoyApp.sub_title"
  - "3 unit tests for main() entry point (test_version_flag, test_version_flag_unknown, test_no_version_flag_launches_app)"
  - "Full README.md with installation, first-run setup, and key bindings reference"
affects: [future-distribution, uv-tool-install, user-onboarding]

# Tech tracking
tech-stack:
  added: [importlib.metadata (stdlib)]
  patterns:
    - "Lazy import of importlib.metadata via shared _get_version() helper (CP-2 pattern) to avoid startup overhead on normal TUI launches"
    - "`in sys.argv` check (not index-based) before JoyApp instantiation to handle uv run -- forwarding correctly"
    - "Version string surfaced in TUI header via self.sub_title = _get_version() on mount"

key-files:
  created:
    - tests/test_main.py
    - README.md
  modified:
    - src/joy/app.py
    - src/joy/screens/settings.py
    - src/joy/widgets/project_list.py

key-decisions:
  - "Use sys.argv direct check (no argparse) per D-11 -- simpler, zero overhead for normal launches"
  - "Switch from `sys.argv[1] == '--version'` to `'--version' in sys.argv` to handle `uv run joy -- --version` correctly (UAT feedback)"
  - "Extract _get_version() helper so both main() and JoyApp.sub_title share one implementation"
  - "Use actual GitHub URL (pietercusters/joy) in README install command based on discovered git remote"
  - "MGMT-04 (J/K reorder) NOT implemented -- deferred per D-13"

patterns-established:
  - "Lazy import pattern for stdlib modules only needed in specific CLI branches"
  - "_is_filtered flag on ProjectList tracks Enter-kept filter state so Escape can always restore full list"

requirements-completed: [MGMT-04, DIST-01, DIST-03, DIST-04]

# Metrics
duration: ~25min
completed: 2026-04-11
tasks_completed: 3
files_modified: 5
---

# Phase 5 Plan 03: --version Flag and README Summary

**sys.argv --version flag with importlib.metadata, version in TUI sub-title, and full README covering installation, setup, and key bindings -- UAT-verified**

## Performance

- **Duration:** ~25 min (Tasks 1-2 ~15 min, Task 3 UAT + fixes ~10 min)
- **Completed:** 2026-04-11
- **Tasks:** 3 of 3 (all complete including human-verify checkpoint)
- **Files modified:** 5
- **Tests:** 131 passed, 1 deselected

## What Was Built

### Task 1: --version flag and unit tests

Modified `src/joy/app.py`:
- Added `import sys` at top level
- Added `_get_version()` helper (after UAT) that lazily imports `importlib.metadata` and returns the installed version or `"unknown"` on `PackageNotFoundError`
- Updated `main()` to check `"--version" in sys.argv` (not index-based) before `JoyApp` instantiation, printing `joy {_get_version()}` and returning
- Added `self.sub_title = _get_version()` in `JoyApp.on_mount()` so the version appears in the TUI header

Created `tests/test_main.py` with 3 unit tests:
- `test_version_flag`: asserts stdout starts with `"joy "` when `--version` is in argv
- `test_version_flag_unknown`: asserts output is `"joy unknown"` when `PackageNotFoundError` is raised
- `test_no_version_flag_launches_app`: asserts `JoyApp().run()` is called when no `--version` flag

### Task 2: README

Created `README.md` at project root replacing the 2-line placeholder stub:
- Installation section with `uv tool install git+https://github.com/pietercusters/joy`
- `joy --version` verification step
- First-run setup section documenting `~/.joy/config.toml` fields with a settings table
- Usage section with complete key bindings for global, project list, and detail panes
- Object types table with all 9 presets (mr, branch, ticket, thread, file, note, worktree, agents, url)
- Platform requirements and MIT license

### Task 3: Human verification (checkpoint:human-verify)

Human ran all Phase 5 features and provided UAT feedback. All issues were resolved in a post-checkpoint fix commit (a62b065).

## Commits

| Hash | Task | Description |
|------|------|-------------|
| a813bbe | Task 1 | feat(05-03): add --version flag to main() with importlib.metadata |
| daa77df | Task 2 | feat(05-03): write README with installation, setup, and key bindings |
| a62b065 | Task 3 (UAT) | fix(05-03): address phase 5 UAT feedback |

## Deviations from Plan

### Auto-fixed Issues (post-checkpoint UAT feedback)

**1. [Rule 1 - Bug] `--version` failed when invoked as `uv run joy -- --version`**
- **Found during:** Task 3 human verification
- **Issue:** `sys.argv[1] == "--version"` requires `--version` at index 1 exactly. When `uv run` adds a `--` separator, the position shifts and the check fails.
- **Fix:** Changed to `"--version" in sys.argv` -- position-independent, handles any invocation style.
- **Files modified:** src/joy/app.py
- **Commit:** a62b065

**2. [Rule 2 - Missing functionality] Version not visible inside TUI**
- **Found during:** Task 3 human verification
- **Issue:** After a clean `joy` launch, there was no way to know which version was running from within the TUI itself.
- **Fix:** Added `self.sub_title = _get_version()` in `JoyApp.on_mount()`. Textual displays sub_title in the header bar.
- **Files modified:** src/joy/app.py
- **Commit:** a62b065

**3. [Rule 2 - Missing functionality] Extracted `_get_version()` helper to share implementation**
- **Found during:** Task 3 (implementing fix 2 above required version lookup at TUI mount time)
- **Issue:** The `--version` branch had an inline `importlib.metadata` block. Reusing that in `on_mount()` would duplicate the error-handling logic.
- **Fix:** Extracted `_get_version()` module-level function. Both `main()` and `on_mount()` call it.
- **Files modified:** src/joy/app.py
- **Commit:** a62b065

**4. [Rule 1 - Bug] Settings modal layout was too spread out; Save button was full-width**
- **Found during:** Task 3 human verification (settings layout feedback)
- **Issue:** Excessive vertical padding and a full-width Save button made the modal feel unpolished.
- **Fix:** Reduced padding (`padding: 0 2 1 2`), removed per-field top margin from `.field-label`, reduced SelectionList max-height to 9, set `Button { width: auto }` and `margin-top: 1` for a compact inline button.
- **Files modified:** src/joy/screens/settings.py
- **Commit:** a62b065

**5. [Rule 1 - Bug] Settings hint text referenced non-existent "Enter" shortcut**
- **Found during:** Task 3 human verification
- **Issue:** Hint read "Tab to navigate, Enter / Save Settings to save, Escape to cancel" but Enter does not submit the modal.
- **Fix:** Updated hint to "Tab to navigate · Save Settings to save · Escape to cancel".
- **Files modified:** src/joy/screens/settings.py
- **Commit:** a62b065

**6. [Rule 1 - Bug] Escape after Enter-kept filter did not restore the full project list**
- **Found during:** Task 3 human verification (filter mode feedback)
- **Issue:** Pressing `/`, typing, pressing `Enter` (keep filtered list) then `Escape` did not restore the full list -- the `_filter_active` flag was already `False` after `Enter`, so the Escape handler no-oped.
- **Fix:** Added `_is_filtered: bool` flag on `ProjectList`. Set to `True` on `on_input_submitted`. Escape handler checks `listview._filter_active or self._is_filtered`. `_exit_filter_mode()` clears both flags. Re-entering filter mode also clears `_is_filtered` to avoid stale state.
- **Files modified:** src/joy/widgets/project_list.py
- **Commit:** a62b065

## Known Stubs

None - all content wired to real data. `importlib.metadata` reads the actual installed version; README documents actual functionality; all TUI features verified working.

## Threat Flags

None. No new network endpoints, auth paths, or trust boundaries beyond what the plan's threat model covered.

## Self-Check: PASSED

Files verified:
- FOUND: src/joy/app.py (import sys, _get_version(), "--version" in sys.argv, self.sub_title)
- FOUND: tests/test_main.py (test_version_flag, test_version_flag_unknown, test_no_version_flag_launches_app)
- FOUND: README.md (uv tool install, Key Bindings, object types table)
- FOUND: src/joy/screens/settings.py (UAT layout fixes, corrected hint text)
- FOUND: src/joy/widgets/project_list.py (_is_filtered flag, corrected Escape handler)

Commits verified:
- FOUND: a813bbe (Task 1 - --version flag)
- FOUND: daa77df (Task 2 - README)
- FOUND: a62b065 (Task 3 - UAT fixes)

Test suite: 131 passed, 1 deselected (full green)
