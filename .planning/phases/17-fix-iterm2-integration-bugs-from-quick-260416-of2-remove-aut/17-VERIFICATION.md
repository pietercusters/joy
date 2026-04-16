---
phase: 17-fix-iterm2-integration-bugs
verified: 2026-04-16T18:45:00Z
status: human_needed
score: 9/9
overrides_applied: 0
human_verification:
  - test: "Press h on a project with no linked tab and confirm a new iTerm2 tab is created and linked"
    expected: "A new iTerm2 tab appears, project.iterm_tab_id is persisted, subsequent h press activates the same tab"
    why_human: "Requires live iTerm2 connection and interaction with macOS UI — cannot be verified programmatically"
  - test: "Press h on a project with a live tab and confirm the tab is activated (focused)"
    expected: "The existing iTerm2 tab is brought to the front; no duplicate tab is created"
    why_human: "Requires live iTerm2 connection and visual confirmation of window focus"
  - test: "Close an iTerm2 tab externally, then wait for refresh cycle — confirm notification 'press h to relink'"
    expected: "A Textual notification appears with the project name and 'press h to relink' text; iterm_tab_id is cleared"
    why_human: "Requires live iTerm2, refresh timing, and reading on-screen notification text"
  - test: "Delete a project that has an iterm_tab_id set — confirm the iTerm2 tab is closed"
    expected: "After confirming the delete modal, the linked iTerm2 tab disappears from iTerm2"
    why_human: "Requires live iTerm2 and visual inspection of tab bar after delete"
  - test: "Archive a project that has an iterm_tab_id set — confirm tab closes and no ArchiveChoice modal appears"
    expected: "ConfirmationModal appears (not ArchiveModal), after confirm the iTerm2 tab closes and project moves to archive"
    why_human: "Requires live iTerm2 and end-to-end UI flow validation"
---

# Phase 17: Fix iTerm2 Integration Bugs — Verification Report

**Phase Goal:** Remove automatic iTerm2 tab creation (tabs only via h-key), close entire tab on project delete/archive, isolate all tests from real ~/.joy/ paths
**Verified:** 2026-04-16T18:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All tests use isolated tmp paths for store constants — no test ever reads or writes ~/.joy/ | VERIFIED | conftest.py lines 46-61: autouse session fixture with all 5 setattr calls (JOY_DIR, PROJECTS_PATH, CONFIG_PATH, REPOS_PATH, ARCHIVE_PATH) pointing to tmp dir; mp.undo() teardown present |
| 2 | close_tab(tab_id) function exists in terminal_sessions.py and follows the same lazy-import, silent-fail pattern as close_session | VERIFIED | terminal_sessions.py lines 225-253: function exists with lazy `import iterm2`, nonlocal success pattern, try/except around Connection().run_until_complete, tab.async_close call |
| 3 | No iTerm2 tab is auto-created during refresh cycles | VERIFIED | app.py _set_terminal_sessions (lines 246-255): elif branch for auto-create completely removed; only stale-heal if branch remains |
| 4 | No iTerm2 tab is auto-created when a new project is created via n key | VERIFIED | app.py action_new_project (lines 614-639): no call to _do_create_tab_for_project; only _start_add_object_loop remains |
| 5 | Pressing h on a project with no linked tab creates one; pressing h on a project with a live tab activates it | VERIFIED (code) | app.py action_open_terminal (lines 809-826): if iterm_tab_id -> _do_activate_tab; else with _tabs_creating guard -> _do_create_tab_for_project |
| 6 | Stale tabs are cleared silently with a notification telling user to press h to relink | VERIFIED | app.py line 253: self.notify with "press h to relink" in stale-heal branch |
| 7 | Deleting a project closes its entire iTerm2 tab | VERIFIED | project_list.py lines 483-485: on_confirm checks iterm_tab_id, calls self.app._close_tab_bg before projects.remove |
| 8 | Archiving a project closes its entire iTerm2 tab (no choice offered) | VERIFIED | project_list.py lines 566-568: on_archive checks iterm_tab_id, calls self.app._close_tab_bg; uses ConfirmationModal not ArchiveModal |
| 9 | ArchiveModal is removed — archive uses ConfirmationModal instead | VERIFIED | src/joy/screens/archive_modal.py deleted; screens/__init__.py has no ArchiveModal/ArchiveChoice exports; all source .py files have zero ArchiveModal/ArchiveChoice references |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/conftest.py` | Autouse session-scoped fixture patching all joy.store path constants | VERIFIED | Contains _isolated_store_paths, all 5 setattr calls, mp.undo() teardown |
| `src/joy/terminal_sessions.py` | close_tab function for closing entire iTerm2 tab by tab_id | VERIFIED | def close_tab at line 225, follows close_session pattern exactly |
| `src/joy/app.py` | _close_tab_bg worker, modified _set_terminal_sessions (no auto-create), modified action_open_terminal (create on h), modified action_new_project (no auto-create) | VERIFIED | All four edits confirmed at lines 253, 614-639, 809-826, 898-902 |
| `src/joy/widgets/project_list.py` | Modified action_delete_project and action_archive_project calling _close_tab_bg | VERIFIED | _close_tab_bg called in both methods (lines 485, 568) |
| `src/joy/screens/__init__.py` | Clean exports without ArchiveModal/ArchiveChoice | VERIFIED | File contains only 8 imports/exports, no ArchiveModal/ArchiveChoice |
| `src/joy/screens/archive_modal.py` | Deleted | VERIFIED | File does not exist; only __pycache__ .pyc remains (harmless) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| tests/conftest.py | joy.store | monkeypatch setattr on 5 path constants | WIRED | All 5 setattr calls on lines 55-59 of conftest.py |
| terminal_sessions.py:close_tab | iterm2 Tab.async_close | lazy import + Connection().run_until_complete | WIRED | line 243: await tab.async_close(force=force) inside _close inner function |
| app.py:_close_tab_bg | joy.terminal_sessions.close_tab | lazy import in @work thread | WIRED | line 901: from joy.terminal_sessions import close_tab |
| project_list.py:action_delete_project | app.py:_close_tab_bg | self.app._close_tab_bg(project.iterm_tab_id) | WIRED | line 485: call inside if project.iterm_tab_id guard |
| project_list.py:action_archive_project | app.py:_close_tab_bg | self.app._close_tab_bg(project.iterm_tab_id) | WIRED | line 568: call inside if project.iterm_tab_id guard |
| app.py:action_open_terminal | app.py:_do_create_tab_for_project | h key creates tab when iterm_tab_id is None | WIRED | line 826: call in else branch with _tabs_creating guard |

### Data-Flow Trace (Level 4)

Not applicable — all changes are control-flow modifications (removing branches, adding calls). No new data rendering paths introduced.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| close_tab importable | `uv run python -c "from joy.terminal_sessions import close_tab; print('OK')"` | close_tab OK | PASS |
| JoyApp importable | `uv run python -c "from joy.app import JoyApp; print('OK')"` | JoyApp OK | PASS |
| ConfirmationModal importable | `uv run python -c "from joy.screens import ConfirmationModal; print('OK')"` | ConfirmationModal OK | PASS |
| ProjectList importable | `uv run python -c "from joy.widgets.project_list import ProjectList; print('OK')"` | ProjectList OK | PASS |
| Non-pre-existing tests pass | `uv run pytest tests/ -q --ignore=test_propagation.py --ignore=test_sync.py --ignore=test_refresh.py` | 304 passed, 42 deselected | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| FIX17-TEST-ISOLATION | 17-01-PLAN.md | All tests use isolated tmp paths, no test touches ~/.joy/ | SATISFIED | conftest.py autouse fixture with all 5 store constants patched |
| FIX17-CLOSE-TAB | 17-01-PLAN.md | close_tab(tab_id) function exists in terminal_sessions.py | SATISFIED | Function at lines 225-253, lazy-import + silent-fail pattern |
| FIX17-REMOVE-AUTO-SYNC | 17-02-PLAN.md | No auto-create of iTerm2 tabs in refresh or new-project flows | SATISFIED | elif auto-create branch removed; action_new_project no longer calls _do_create_tab_for_project |
| FIX17-TAB-CLOSE-ON-DELETE-ARCHIVE | 17-02-PLAN.md | Delete and archive both close entire iTerm2 tab | SATISFIED | _close_tab_bg called in both action_delete_project and action_archive_project |

**Note:** FIX17-* requirement IDs are phase-local bug-fix requirements defined in ROADMAP.md. They do not appear in REQUIREMENTS.md (which covers v1.2 feature requirements). All 4 FIX17 IDs are fully accounted for and satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/joy/widgets/project_list.py | 658 | `placeholder=` text in Input widget | Info | UI placeholder text for a filter input — not a code stub. No impact on phase 17 goals. |

No blockers or warnings found. The single Info-level hit is a UI placeholder string in an Input widget, unrelated to this phase.

### Human Verification Required

#### 1. h-key tab creation

**Test:** With a project that has no iTerm2 tab linked, press h in the project list
**Expected:** A new iTerm2 tab is created, the project gains an iterm_tab_id, and pressing h again activates the same tab without creating a duplicate
**Why human:** Requires live iTerm2 connection and macOS UI interaction — cannot be verified programmatically without running the app

#### 2. h-key tab activation

**Test:** With a project that has a live linked tab, press h
**Expected:** The existing iTerm2 tab is brought to the foreground; no new tab is created
**Why human:** Requires live iTerm2 and visual confirmation of window focus behavior

#### 3. Stale tab notification

**Test:** Link a project to an iTerm2 tab, close that tab in iTerm2, wait for next refresh cycle
**Expected:** A Textual notification appears with the project name and "press h to relink"; project's iterm_tab_id is cleared
**Why human:** Requires live iTerm2, timing synchronization with refresh cycle, and reading on-screen notification text

#### 4. Delete closes tab

**Test:** Link a project to an iTerm2 tab, then delete the project via d key and confirm the deletion modal
**Expected:** The iTerm2 tab closes before (or immediately after) the project is removed from the list
**Why human:** Requires live iTerm2 and visual inspection of the tab bar after the delete confirmation

#### 5. Archive closes tab, ConfirmationModal appears

**Test:** Link a project to an iTerm2 tab, then archive the project via a key
**Expected:** A ConfirmationModal appears (with "Enter to archive, Escape to cancel" footer hint, NOT the old ArchiveModal with choices), and after confirming, the iTerm2 tab closes and the project appears in the archive browser
**Why human:** Requires live iTerm2 and end-to-end UI flow validation including visual modal inspection

### Gaps Summary

No gaps found. All 9 observable truths are verified, all 6 key links are wired, all 4 requirements are satisfied, all artifacts are substantive and wired. The phase goal is fully achieved at the code level.

Human verification is required for 5 iTerm2-interaction behaviors that cannot be tested without a running app and live iTerm2 connection. These are standard interactive UI tests, not indicators of missing implementation.

---

_Verified: 2026-04-16T18:45:00Z_
_Verifier: Claude (gsd-verifier)_
