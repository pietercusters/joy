---
phase: 16-live-data-propagation
verified: 2026-04-15T10:30:00Z
status: human_needed
score: 13/13
overrides_applied: 0
human_verification:
  - test: "Kill an iTerm2 session that matches an AGENTS object value on a project, then trigger a refresh cycle in joy (press 'r'). Observe the project detail pane."
    expected: "The agent row dims (muted color, italic text) and a toast notification appears: 'Agent offline in <project>'"
    why_human: "CSS visual rendering and Textual toast display cannot be verified without a running TUI. The stale flag is set correctly in code but the visual dimming requires live rendering."
  - test: "After the session is killed, bring the same iTerm2 session back (create a session with the same name). Trigger another refresh cycle."
    expected: "The agent row returns to normal styling and a toast notification appears: 'Agent back online in <project>'"
    why_human: "Stale-clearing visual transition requires live TUI and live iTerm2 session state."
  - test: "Create a git branch in a repo that matches a project's BRANCH object value, open a PR/MR for it on GitHub/GitLab, then trigger a refresh in joy."
    expected: "A new MR row appears in the project's detail pane and a toast notification shows the PR number and project name. The MR persists on subsequent refreshes (no duplicate added)."
    why_human: "MR auto-add requires a live PR on GitHub/GitLab and a live MR fetch. Cannot be tested without external forge connectivity and a real project setup."
  - test: "Observe the full app with multiple projects, some with agents that are offline. Verify the stale rows are visually distinguishable from live rows."
    expected: "Offline agent rows show muted color on all three columns (icon, value, kind) and italic text on value and kind columns. Live agent rows show normal bright text."
    why_human: "Visual differentiation quality ('visually distinguishable') requires human judgment of rendered output."
---

# Phase 16: Live Data Propagation — Verification Report

**Phase Goal:** Background refresh automatically keeps project objects in sync with live MR and agent state -- auto-adding MR objects and marking/unmarking agent objects stale (PROP-01 and PROP-03 dropped per D-01: worktree objects managed by WorktreePane live display)
**Verified:** 2026-04-15T10:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | When an MR is detected for a project's branch and no MR object with that URL exists, it is silently auto-added | VERIFIED | `_propagate_mr_auto_add` in app.py:235-271 checks URL dedup and appends `ObjectItem(kind=MR)`. 8 unit tests in `TestMRAutoAdd` pass. |
| SC-2 | When an agent session disappears from iTerm2, its project object is visually dimmed (stale); when the session reappears, the stale marker clears | VERIFIED | `_propagate_agent_stale` sets `obj.stale = is_now_absent`. `--stale` CSS class applied in `_render_project` line 157. 7 unit tests in `TestAgentStale` pass. Visual rendering needs human confirm (see below). |
| SC-3 | MR objects are auto-added but never auto-removed by propagation; branch objects are never modified by propagation | VERIFIED | No MR removal code exists in any propagation method. `_propagate_agent_stale` skips non-AGENTS objects via `if obj.kind != PresetKind.AGENTS: continue`. Tests `test_mr_never_removed` and `test_branch_never_modified` pass. |
| SC-4 | Projects without a registered repo are completely excluded from all propagation — their objects are never touched | VERIFIED | `_propagate_mr_auto_add` line 247: `if project.repo is None: continue`. Agent stale marking has no repo check by design (agents are session-name based, not repo-based). Test `test_mr_no_repo_excluded` passes. |
| SC-5 | PROP-01 (worktree auto-remove) and PROP-03 (worktree move) are dropped — WorktreePane handles worktree display live | VERIFIED | No worktree auto-remove or move logic exists in any propagation method. No references to PROP-01/PROP-03 implementation found in app.py. |

**Roadmap Score:** 5/5 truths verified

### Plan Must-Have Truths (Plan 01 + Plan 02)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| P01-1 | New MR ObjectItem appended when branch matches and no existing MR with same URL | VERIFIED | app.py:263-270, `test_mr_auto_add_appends_object` |
| P01-2 | No duplicate MR if URL already exists | VERIFIED | app.py:257-260, `test_mr_dedup_skips_existing` |
| P01-3 | AGENTS object stale=True when session absent from current iTerm2 sessions | VERIFIED | app.py:280-287, `test_agent_marked_stale_when_absent` |
| P01-4 | Previously-stale AGENTS stale cleared when session reappears | VERIFIED | app.py:289-291, `test_agent_stale_cleared_when_present` |
| P01-5 | Branch objects never touched by propagation | VERIFIED | No BRANCH mutation in either propagation method, `test_branch_never_modified` |
| P01-6 | MR objects never removed by propagation | VERIFIED | No removal logic, `test_mr_never_removed` |
| P01-7 | Projects with repo=None skipped by MR propagation | VERIFIED | app.py:247-248, `test_mr_no_repo_excluded` |
| P01-8 | stale field not serialized to TOML by to_dict() | VERIFIED | to_dict() explicit key list excludes stale. Runtime confirmed: `'stale' not in obj.to_dict()`. |
| P01-9 | All mutations in single cycle result in at most one _save_projects_bg() call | VERIFIED | app.py:305-307: single `mr_added` boolean gates a single `_save_projects_bg()` call |
| P02-1 | AGENTS stale=True → ObjectRow visually dimmed and italicized | VERIFIED (code) / HUMAN (visual) | CSS rules confirmed in ObjectRow.DEFAULT_CSS. `add_class("--stale")` in project_detail.py:158. Visual rendering requires human confirm. |
| P02-2 | AGENTS stale=False → ObjectRow renders normally (no --stale class) | VERIFIED | `getattr(item, 'stale', False)` guard in project_detail.py:157 prevents class addition. `TestStaleCSSIntegration` tests pass. |
| P02-3 | New MR object appears in ProjectDetail on next render | VERIFIED | `_propagate_changes` calls `project_list.set_projects` + `ProjectDetail.set_project` when messages exist (app.py:313-323) |
| P02-4 | Status bar shows brief notification when propagation makes a change | VERIFIED | `self.notify(msg, markup=False)` called per message in app.py:310-311. Textual `notify()` renders toast notifications. |

**Plan Must-Have Score:** 13/13 truths verified (P02-1 visual quality pending human)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/models.py` | ObjectItem with stale: bool = False runtime field | VERIFIED | Line 57: `stale: bool = False  # Runtime-only; not serialized to TOML (D-07)`. Substantive (189 lines). |
| `src/joy/app.py` | `_propagate_changes`, `_propagate_mr_auto_add`, `_propagate_agent_stale`, `_current_mr_data` | VERIFIED | All four present at lines 84, 235, 273, 294 respectively. Methods are substantive (not stubs). |
| `tests/test_propagation.py` | Unit tests for PROP-02, PROP-04..08 | VERIFIED | 25 tests in 4 classes. 412+ lines. All pass. |
| `src/joy/widgets/object_row.py` | --stale CSS class styles | VERIFIED | Lines 77-87: three CSS rules for `.col-icon`, `.col-value`, `.col-kind` with `$text-muted` and `text-style: italic`. |
| `src/joy/widgets/project_detail.py` | Stale class application during `_render_project` | VERIFIED | Lines 157-158: `if getattr(item, 'stale', False): row.add_class("--stale")` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `src/joy/app.py` | `src/joy/models.py` | `obj.stale` field access in `_propagate_agent_stale` | VERIFIED | app.py:285-287 reads and sets `obj.stale` on `ObjectItem` instances |
| `src/joy/app.py` | `_maybe_compute_relationships` | `_propagate_changes` called after `_update_badges` | VERIFIED | app.py:232-233: `self._update_badges()` then `self._propagate_changes(...)` |
| `src/joy/app.py` | `_maybe_compute_relationships` | Gated by `_worktrees_ready and _sessions_ready` | VERIFIED | app.py:227: `if not (self._worktrees_ready and self._sessions_ready): return` |
| `src/joy/widgets/project_detail.py` | `src/joy/widgets/object_row.py` | `row.add_class("--stale")` when `item.stale` is True | VERIFIED | project_detail.py:157-158: `if getattr(item, 'stale', False): row.add_class("--stale")` |
| `_set_worktrees` | `_maybe_compute_relationships` | Sets `_worktrees_ready = True` then calls gate | VERIFIED | app.py:198, 206: flag set, then gate called |
| `_set_terminal_sessions` | `_maybe_compute_relationships` | Sets `_sessions_ready = True` then calls gate | VERIFIED | app.py:212, 218: flag set, then gate called |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `_propagate_agent_stale` | `active_sessions` | `self._current_sessions` populated from `_set_terminal_sessions` which calls real iTerm2 discovery | Yes — real `TerminalSession` objects from iTerm2 API | FLOWING |
| `_propagate_mr_auto_add` | `mr_data` | `self._current_mr_data` populated from `fetch_mr_data()` at app.py:160 — real GitHub/GitLab API call | Yes — `MRInfo` objects from forge API | FLOWING |
| `ObjectRow.--stale` | `item.stale` | Set by `_propagate_agent_stale` from real session comparison | Yes — computed from live `_current_sessions` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| JoyApp has all 4 propagation methods | `uv run python -c "from joy.app import JoyApp; print(all(hasattr(JoyApp, m) for m in ['_propagate_changes','_propagate_mr_auto_add','_propagate_agent_stale','_maybe_compute_relationships']))"` | True | PASS |
| ObjectRow.DEFAULT_CSS contains all 3 --stale rules | `uv run python -c "from joy.widgets.object_row import ObjectRow; css=ObjectRow.DEFAULT_CSS; print(all(r in css for r in ['ObjectRow.--stale .col-value','ObjectRow.--stale .col-icon','ObjectRow.--stale .col-kind']))"` | True | PASS |
| stale not serialized to TOML | `uv run python -c "from joy.models import ObjectItem,PresetKind; print('stale' not in ObjectItem(kind=PresetKind.AGENTS,value='x',stale=True).to_dict())"` | True | PASS |
| All 25 propagation tests pass | `uv run pytest tests/test_propagation.py -q` | 25 passed in 0.15s | PASS |
| Full test suite (309 tests) | `uv run pytest tests/ -q` | 309 passed, 38 deselected, 1 warning | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| PROP-01 | 16-01 | Worktree auto-remove | DROPPED (D-01) | Intentionally not implemented per ROADMAP SC-5. Acknowledged in plan. |
| PROP-02 | 16-01, 16-02 | MR auto-add | SATISFIED | `_propagate_mr_auto_add` + 8 tests |
| PROP-03 | 16-01 | Worktree move | DROPPED (D-01) | Intentionally not implemented per ROADMAP SC-5. |
| PROP-04 | 16-01, 16-02 | Agent stale visual dimming | SATISFIED (code) / HUMAN (visual) | CSS rules + add_class wiring in place. End-to-end visual requires human testing. |
| PROP-05 | 16-01, 16-02 | Agent stale clearing | SATISFIED | Stale cleared on session reappearance + `test_agent_stale_cleared_*` |
| PROP-06 | 16-01 | Branch objects never modified | SATISFIED | No mutation of BRANCH objects in any propagation method |
| PROP-07 | 16-01 | MR never auto-removed | SATISFIED | No removal code. `test_mr_never_removed` passes. |
| PROP-08 | 16-01 | Projects without repo excluded | SATISFIED | `project.repo is None` guard at app.py:247 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/joy/app.py` | 305 | `any("\u2295 Added PR" in m ...)` — save decision coupled to unicode message string | WARNING | If MR message format changes, TOML save silently stops triggering. Flagged as WR-02 in code review. No test coverage for this coupling. Not a goal blocker today. |
| `src/joy/app.py` | 319-320 | `_rows`/`_cursor` read immediately after `set_projects` which uses `call_after_refresh` | WARNING | Reads pre-rebuild state. Benign while no row reordering occurs (WR-01 in review). Not a goal blocker today. |
| `tests/test_propagation.py` | 373-411 | `TestStaleCSSIntegration` replicates production logic pattern rather than calling `_render_project` | WARNING | Tests verify the test author's inline code, not the production `_render_project`. If `_render_project` lost its `add_class("--stale")` call, these tests would still pass. (IN-02 in review). |

No MISSING, STUB, or PLACEHOLDER patterns found. No TODO/FIXME comments in phase 16 files.

### Human Verification Required

#### 1. Agent Offline Visual Dimming

**Test:** In a live joy session, ensure you have a project with an AGENTS object whose value matches an active iTerm2 session name. Kill that iTerm2 session (close it or rename it). Press 'r' to trigger a refresh.
**Expected:** The AGENTS row in the project detail pane visually dims — icon, value, and kind columns all show in muted/grey color, with value and kind in italic text. A toast notification appears briefly at the top-right reading something like "● Agent 'session-name' offline in project-name".
**Why human:** CSS visual rendering (color, italic) and Textual toast notifications cannot be verified by static code analysis. The CSS rules exist and add_class is wired, but the actual rendering quality requires a running TUI.

#### 2. Agent Back Online Visual Restoration

**Test:** After completing Test 1 (agent shown as stale), recreate the iTerm2 session with the exact same name. Press 'r' to trigger another refresh.
**Expected:** The AGENTS row returns to its normal bright styling (no dim, no italic). A toast notification appears: "● Agent 'session-name' back online in project-name".
**Why human:** State transition from stale back to live requires live iTerm2 interaction and visual confirmation of CSS class removal.

#### 3. MR Auto-Add End-to-End

**Test:** Set up a project in joy with a registered repo and a BRANCH object matching an active git branch. Open a PR/MR for that branch on GitHub or GitLab. Trigger a refresh in joy.
**Expected:** A new MR row appears in the project detail pane (with the PR number as label) and a toast notification shows. Triggering another refresh does not create a duplicate MR row.
**Why human:** Requires a live external forge (GitHub/GitLab), real API credentials, and a real PR — cannot be mocked in automated tests.

#### 4. Multiple Projects Mix Stale/Live

**Test:** With 2+ projects each having different AGENTS objects — some session names active, some not — trigger a refresh.
**Expected:** Only the offline agents show dimmed styling. Online agents render normally. The stale and live rows are visually distinguishable side by side.
**Why human:** Multi-project rendering quality requires human judgment of visual output.

### Gaps Summary

No gaps found. All 13 automated must-haves are verified. Three review warnings (WR-01, WR-02, IN-02) are present but do not block the phase goal — they represent code quality improvements for future phases, not missing functionality.

The phase requires human verification for the visual end-to-end flow (Plan 02, Task 2 was explicitly marked `awaiting-human` in the SUMMARY). This is expected and by design.

---

_Verified: 2026-04-15T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
