---
phase: 17-fix-iterm2-integration-bugs
verified: 2026-04-16T19:30:00Z
status: human_needed
score: 10/10
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 9/9
  gaps_closed:
    - "Pressing h on a project with no linked iTerm2 tab creates a new tab AND focuses it immediately (create_tab now calls await tab.async_select() + await app.async_activate())"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Press h on a project with no linked tab and confirm the new iTerm2 tab is created AND immediately focused"
    expected: "A new iTerm2 tab appears, it is immediately brought to the front (iTerm2 window activates), project.iterm_tab_id is persisted, subsequent h press activates the same tab"
    why_human: "Requires live iTerm2 connection and visual confirmation that the tab is focused — unit test confirms the API calls are made but cannot confirm visual focus behavior"
  - test: "Press h on a project with a live tab and confirm the tab is activated (focused)"
    expected: "The existing iTerm2 tab is brought to the front; no duplicate tab is created"
    why_human: "Requires live iTerm2 connection and visual confirmation of window focus — previously PASSED in UAT, regression check needed after Plan 03 changes"
  - test: "Close an iTerm2 tab externally, then wait for refresh cycle — confirm notification 'press h to relink'"
    expected: "A Textual notification appears with the project name and 'press h to relink' text; iterm_tab_id is cleared"
    why_human: "Requires live iTerm2, refresh timing, and reading on-screen notification text — previously PASSED in UAT"
  - test: "Delete a project that has an iterm_tab_id set — confirm the iTerm2 tab is closed"
    expected: "After confirming the delete modal, the linked iTerm2 tab disappears from iTerm2"
    why_human: "Requires live iTerm2 and visual inspection of tab bar after delete — previously PASSED in UAT"
  - test: "Archive a project that has an iterm_tab_id set — confirm tab closes and no ArchiveChoice modal appears"
    expected: "ConfirmationModal appears (not ArchiveModal), after confirm the iTerm2 tab closes and project moves to archive"
    why_human: "Requires live iTerm2 and end-to-end UI flow validation — previously PASSED in UAT"
---

# Phase 17: Fix iTerm2 Integration Bugs — Verification Report

**Phase Goal:** Remove automatic iTerm2 tab creation (tabs only via h-key), close entire tab on project delete/archive, isolate all tests from real ~/.joy/ paths
**Verified:** 2026-04-16T19:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (Plan 17-03)

## Re-verification Summary

| Item | Previous | Current | Change |
|------|----------|---------|--------|
| h-key tab focus after creation | FAILED (UAT gap) | VERIFIED (code) | Gap closed |
| h-key tab activation (existing) | PASSED (UAT) | VERIFIED (code, unchanged) | Regression check pass |
| Stale tab notification | PASSED (UAT) | VERIFIED (code, unchanged) | Regression check pass |
| Delete closes tab | PASSED (UAT) | VERIFIED (code, unchanged) | Regression check pass |
| Archive closes tab + ConfirmationModal | PASSED (UAT) | VERIFIED (code, unchanged) | Regression check pass |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All tests use isolated tmp paths for store constants — no test ever reads or writes ~/.joy/ | VERIFIED | tests/conftest.py lines 46-61: autouse session fixture with all 5 setattr calls (JOY_DIR, PROJECTS_PATH, CONFIG_PATH, REPOS_PATH, ARCHIVE_PATH) pointing to tmp_path_factory dir; mp.undo() teardown present |
| 2 | close_tab(tab_id) function exists in terminal_sessions.py and follows the same lazy-import, silent-fail pattern as close_session | VERIFIED | terminal_sessions.py lines 227-255: function exists with lazy import iterm2, nonlocal success pattern, try/except around Connection().run_until_complete, tab.async_close call |
| 3 | No iTerm2 tab is auto-created during refresh cycles | VERIFIED | app.py _set_terminal_sessions (lines 246-255): elif auto-create branch completely removed; only stale-heal if branch remains with notify call |
| 4 | No iTerm2 tab is auto-created when a new project is created via n key | VERIFIED | app.py action_new_project (lines 614-639): no call to _do_create_tab_for_project; only _start_add_object_loop remains after notify |
| 5 | Pressing h on a project with no linked tab creates one; pressing h on a project with a live tab activates it | VERIFIED | app.py action_open_terminal (lines 809-826): if iterm_tab_id -> _do_activate_tab; else with _tabs_creating guard -> _do_create_tab_for_project |
| 6 | Stale tabs are cleared silently with a notification telling user to press h to relink | VERIFIED | app.py line 253: self.notify(f"'{project.name}' tab closed \u2014 press h to relink", markup=False) in stale-heal branch |
| 7 | Deleting a project closes its entire iTerm2 tab | VERIFIED | project_list.py lines 483-485: on_confirm checks iterm_tab_id, calls self.app._close_tab_bg(project.iterm_tab_id) before projects.remove |
| 8 | Archiving a project closes its entire iTerm2 tab (no choice offered — always closes) | VERIFIED | project_list.py lines 566-568: on_archive checks iterm_tab_id, calls self.app._close_tab_bg(project.iterm_tab_id); uses ConfirmationModal not ArchiveModal |
| 9 | ArchiveModal is removed — archive uses ConfirmationModal instead | VERIFIED | src/joy/screens/archive_modal.py deleted (confirmed absent); screens/__init__.py has no ArchiveModal/ArchiveChoice exports or imports; zero ArchiveModal/ArchiveChoice references in all .py source files |
| 10 | Pressing h on a project with no linked iTerm2 tab creates a new tab AND focuses it immediately | VERIFIED | terminal_sessions.py create_tab lines 163-164: await tab.async_select() + await app.async_activate() added after result = tab.tab_id; test_terminal_sessions.py lines 397-398: mock_tab.async_select.assert_called_once() and mock_app.async_activate.assert_called_once() assert the focus calls are made |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/conftest.py` | Autouse session-scoped fixture patching all joy.store path constants | VERIFIED | Contains _isolated_store_paths with all 5 setattr calls and mp.undo() teardown |
| `src/joy/terminal_sessions.py` | close_tab function + create_tab with auto-focus | VERIFIED | close_tab at lines 227-255 follows close_session pattern; create_tab at lines 140-170 includes async_select + async_activate |
| `src/joy/app.py` | _close_tab_bg worker, no auto-sync in _set_terminal_sessions, action_open_terminal creates on h, action_new_project has no auto-create | VERIFIED | All four edits confirmed: stale-heal notify at line 253; action_new_project clean at lines 614-639; action_open_terminal with guard at lines 809-826; _close_tab_bg at lines 898-902 |
| `src/joy/widgets/project_list.py` | Modified action_delete_project and action_archive_project calling _close_tab_bg | VERIFIED | _close_tab_bg called at line 485 (delete) and line 568 (archive), both behind iterm_tab_id guard |
| `src/joy/screens/__init__.py` | Clean exports without ArchiveModal/ArchiveChoice | VERIFIED | 8 imports/exports, no ArchiveModal/ArchiveChoice present |
| `src/joy/screens/archive_modal.py` | Deleted | VERIFIED | File confirmed absent from filesystem |
| `tests/test_terminal_sessions.py` | Updated mock for create_tab test covering async_select and async_activate calls | VERIFIED | Lines 370, 377, 397-398: mock_tab.async_select = AsyncMock(), mock_app.async_activate = AsyncMock(), both asserted called_once |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| tests/conftest.py | joy.store | monkeypatch setattr on 5 path constants | WIRED | Lines 55-59: all 5 setattr calls |
| terminal_sessions.py:close_tab | iterm2 Tab.async_close | lazy import + Connection().run_until_complete | WIRED | Line 245: await tab.async_close(force=force) inside _close coroutine |
| terminal_sessions.py:create_tab | iterm2 Tab.async_select + App.async_activate | await calls inside _create coroutine | WIRED | Lines 163-164: await tab.async_select() and await app.async_activate() after result = tab.tab_id |
| app.py:_close_tab_bg | joy.terminal_sessions.close_tab | lazy import in @work thread | WIRED | Line 901: from joy.terminal_sessions import close_tab inside _close_tab_bg |
| project_list.py:action_delete_project | app.py:_close_tab_bg | self.app._close_tab_bg(project.iterm_tab_id) | WIRED | Line 485: call inside if project.iterm_tab_id guard |
| project_list.py:action_archive_project | app.py:_close_tab_bg | self.app._close_tab_bg(project.iterm_tab_id) | WIRED | Line 568: call inside if project.iterm_tab_id guard |
| app.py:action_open_terminal | app.py:_do_create_tab_for_project | h key creates tab when iterm_tab_id is None | WIRED | Line 826: call in else branch with _tabs_creating guard |

### Data-Flow Trace (Level 4)

Not applicable — all changes are control-flow modifications (removing branches, adding calls, adding focus after create). No new data rendering paths introduced.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| terminal_sessions importable (close_tab + create_tab) | python -c "from joy.terminal_sessions import close_tab, create_tab; print('OK')" | terminal_sessions OK | PASS |
| create_tab has async_select call | grep "await tab.async_select()" src/joy/terminal_sessions.py | line 163 match | PASS |
| create_tab has async_activate call | grep "await app.async_activate()" src/joy/terminal_sessions.py | lines 164 + 277 match | PASS |
| Test asserts focus calls | grep "async_select" tests/test_terminal_sessions.py | lines 370, 397 match | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| FIX17-TEST-ISOLATION | 17-01-PLAN.md | All tests use isolated tmp paths, no test touches ~/.joy/ | SATISFIED | conftest.py autouse fixture with all 5 store constants patched to tmp dir |
| FIX17-CLOSE-TAB | 17-01-PLAN.md, 17-03-PLAN.md | close_tab(tab_id) function exists; create_tab focuses new tab | SATISFIED | close_tab at lines 227-255; create_tab focus at lines 163-164; test at lines 370, 377, 397-398 |
| FIX17-REMOVE-AUTO-SYNC | 17-02-PLAN.md | No auto-create of iTerm2 tabs in refresh or new-project flows | SATISFIED | elif auto-create branch removed from _set_terminal_sessions; action_new_project does not call _do_create_tab_for_project |
| FIX17-TAB-CLOSE-ON-DELETE-ARCHIVE | 17-02-PLAN.md | Delete and archive both close entire iTerm2 tab | SATISFIED | _close_tab_bg called in action_delete_project (line 485) and action_archive_project (line 568) |

**Note:** FIX17-* requirement IDs are phase-local bug-fix requirements defined in ROADMAP.md. They do not appear in REQUIREMENTS.md (which tracks v1.2 feature requirements only). All 4 FIX17 IDs are fully accounted for and satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/joy/widgets/project_list.py | ~658 | `placeholder=` text in Input widget | Info | UI placeholder text for a filter input — not a code stub. No impact on phase 17 goals. |

No blockers or warnings. The single Info-level hit is unchanged from the previous verification pass — a UI placeholder string in an Input widget unrelated to this phase.

### Human Verification Required

#### 1. h-key creates and focuses new tab (gap closure verification)

**Test:** With a project that has no iTerm2 tab linked, press h in the project list
**Expected:** A new iTerm2 tab is created AND immediately focused (iTerm2 window comes to foreground, new tab is selected); project gains an iterm_tab_id; pressing h again activates the same tab without creating a duplicate
**Why human:** The code fix is verified (async_select + async_activate calls confirmed), but actual focus behavior requires live iTerm2 and visual confirmation of window activation

#### 2. h-key activates existing tab (regression check)

**Test:** With a project that has a live linked tab, press h
**Expected:** The existing iTerm2 tab is brought to the foreground; no new tab is created
**Why human:** Previously PASSED in UAT (2026-04-16). Regression check after Plan 03 changes to create_tab — the activation path (action_open_terminal -> _do_activate_tab) is unchanged but confirming no regression is prudent.

#### 3. Stale tab notification (regression check)

**Test:** Link a project to an iTerm2 tab, close that tab in iTerm2, wait for next refresh cycle
**Expected:** A Textual notification appears with the project name and "press h to relink"; project's iterm_tab_id is cleared
**Why human:** Previously PASSED in UAT (2026-04-16). Code path unchanged. Standard regression check.

#### 4. Delete closes tab (regression check)

**Test:** Link a project to an iTerm2 tab, then delete the project via d key and confirm the deletion modal
**Expected:** The iTerm2 tab closes before (or immediately after) the project is removed from the list
**Why human:** Previously PASSED in UAT (2026-04-16). Code path unchanged. Standard regression check.

#### 5. Archive closes tab, ConfirmationModal appears (regression check)

**Test:** Link a project to an iTerm2 tab, then archive the project via a key
**Expected:** A ConfirmationModal appears (with "Enter to archive, Escape to cancel" footer hint, NOT the old ArchiveModal), and after confirming the iTerm2 tab closes and the project appears in the archive browser
**Why human:** Previously PASSED in UAT (2026-04-16). Code path unchanged. Standard regression check.

### Gaps Summary

No gaps. All 10 observable truths are verified, all 7 key links are wired, all 4 requirements are satisfied. The original UAT gap (h-key tab focus) is resolved at code level by Plan 17-03: create_tab now calls await tab.async_select() + await app.async_activate() after creating the tab, matching the existing activate_session pattern.

Human verification items 2-5 are regression checks for behaviors that already PASSED in UAT. Item 1 is verification of the gap closure. None of these indicate missing implementation — the status is human_needed because confirming focus behavior requires live iTerm2 interaction.

---

_Verified: 2026-04-16T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
