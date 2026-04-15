---
phase: 14-relationship-foundation-badges
verified: 2026-04-14T22:00:00Z
status: human_needed
score: 6/7 must-haves verified (1 requires human)
overrides_applied: 0
human_verification:
  - test: "Launch joy (uv run joy), wait for first background refresh (~2-5s), observe all project rows in left pane"
    expected: "Every row shows '{project name}  [branch-icon] N  [robot-icon] M' — both counts visible even when N=0 and M=0. Rows with related worktrees/agents show counts > 0."
    why_human: "Badge rendering requires a running Textual app with real iTerm2 and git worktree data. Cannot verify without live TUI."
  - test: "In a running joy session, navigate WorktreePane to a non-first row (down arrow), wait for next background refresh (30s or press 'r')"
    expected: "Cursor stays on the same worktree after refresh — does not jump to row 0"
    why_human: "DOM rebuild behavior with real timing can only be verified in a live session"
  - test: "In a running joy session, navigate TerminalPane to a non-first session, wait for refresh"
    expected: "Cursor stays on the same session name after refresh — does not jump to row 0"
    why_human: "Same as above — requires live TUI with real iTerm2 sessions"
---

# Phase 14: Relationship Foundation & Badges Verification Report

**Phase Goal:** Users see accurate worktree and agent counts on every project row, proving the cross-pane relationship model works end-to-end
**Verified:** 2026-04-14T22:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each project row displays the correct count of active worktrees belonging to that project (matching by repo + branch/path) | ✓ VERIFIED | `ProjectRow._build_content()` renders `ICON_BRANCH {self._wt_count}`; `ProjectList.update_badges()` calls `index.worktrees_for(row.project)` and pushes count to `row.set_counts()`; `compute_relationships()` implements path-then-branch matching; all 7 resolver tests + 6 badge tests pass |
| 2 | Each project row displays the correct count of active agent sessions belonging to that project (matching by session name) | ✓ VERIFIED | `ProjectRow._build_content()` renders `ICON_CLAUDE {self._agent_count}`; `compute_relationships()` matches `obj.kind == PresetKind.AGENTS` via `agent_to_project[obj.value]`; agent match tests pass |
| 3 | Badge counts update automatically after each background refresh cycle without user intervention | ✓ VERIFIED | `_set_worktrees()` sets `_worktrees_ready=True` then calls `_maybe_compute_relationships()`; `_set_terminal_sessions()` sets `_sessions_ready=True` then calls `_maybe_compute_relationships()`; when both flags are true, `compute_relationships()` fires and `_update_badges()` pushes to `ProjectList`; flags reset before compute so next cycle resets correctly |
| 4 | Switching between projects or triggering a refresh does not cause the WorktreePane or TerminalPane cursor to jump to row 0 — cursors stay on the same worktree/session | ? HUMAN NEEDED | Code verified: `set_worktrees()` captures `(repo_name, branch)` identity before `remove_children()` and restores it after; `set_sessions()` captures `session_name` before rebuild and restores after; clamp fallback `min(saved_index, len-1)` used when item gone. 5 TUI slow tests pass. But live runtime behavior with real data requires human check. |

**Score:** 6/7 must-haves verified (truth 4 needs human confirmation for live runtime behavior)

### Must-Haves from Plan 03 Frontmatter

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every ProjectRow displays two badge counts: worktree count and agent count, always visible even when zero | ✓ VERIFIED | `_build_content()` at line 76: `f" {self.project.name}  {ICON_BRANCH} {self._wt_count}  {ICON_CLAUDE} {self._agent_count}"` — both always included |
| 2 | Badge icons use ICON_BRANCH for worktrees and ICON_CLAUDE for agents | ✓ VERIFIED | Module-level imports at lines 13-14 of project_list.py: `from joy.widgets.worktree_pane import ICON_BRANCH` and `from joy.widgets.terminal_pane import ICON_CLAUDE` |
| 3 | ProjectRow.set_counts(wt_count, agent_count) updates the displayed content without DOM rebuild | ✓ VERIFIED | `set_counts()` at line 78-85: stores counts then calls `self.update(self._build_content())` — Static.update() avoids DOM rebuild |
| 4 | ProjectList.update_badges(index) calls set_counts on every row using counts from the RelationshipIndex | ✓ VERIFIED | `update_badges()` at lines 422-431 iterates `self._rows`, calls `index.worktrees_for(row.project)` and `index.agents_for(row.project)`, then `row.set_counts()` |
| 5 | JoyApp computes the RelationshipIndex after both _set_worktrees and _set_terminal_sessions complete in a refresh cycle | ✓ VERIFIED | `_maybe_compute_relationships()` at line 191-210 guards on `self._worktrees_ready and self._sessions_ready`; both methods set their flag then call `_maybe_compute_relationships()` |
| 6 | JoyApp calls _update_badges() after computing the index, pushing counts to ProjectList | ✓ VERIFIED | Line 210: `self._update_badges()` called at end of `_maybe_compute_relationships()` |
| 7 | Badge counts update on every subsequent refresh cycle (ready-flags reset correctly) | ✓ VERIFIED | Lines 201-202: flags reset to False BEFORE computing (not after), so a fast-arriving next cycle doesn't get false-positive ready signals |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/resolver.py` | RelationshipIndex dataclass + compute_relationships() | ✓ VERIFIED | 110 lines; 5 bidirectional maps; path precedence (D-04); no-repo exclusion (D-05); pure function with no I/O |
| `tests/test_resolver.py` | 7 unit tests for all matching cases | ✓ VERIFIED | 7 tests covering path, branch, agent, path-precedence, no-repo, no-match, empty inputs — all pass |
| `src/joy/widgets/project_list.py` | ProjectRow with set_counts() and badge content; ProjectList with update_badges() | ✓ VERIFIED | set_counts() on line 78; update_badges() on line 422; both ICON imports at module level |
| `src/joy/app.py` | JoyApp with _rel_index, _worktrees_ready, _sessions_ready, _maybe_compute_relationships(), _update_badges() | ✓ VERIFIED | All 5 instance vars on lines 72-76; _maybe_compute_relationships() on line 191; _update_badges() on line 212 |
| `tests/test_project_list.py` | 6 unit tests for ProjectRow badge rendering | ✓ VERIFIED | 6 tests covering name visibility, zero badges, set_counts for wt/agent/both, multiple calls — all pass |
| `src/joy/widgets/worktree_pane.py` | Identity-based cursor preservation in set_worktrees() | ✓ VERIFIED | saved_identity captured on line 312-316; restored on lines 368-375; clamp fallback on line 375 |
| `src/joy/widgets/terminal_pane.py` | SessionRow.session_name + identity-based cursor preservation in set_sessions() | ✓ VERIFIED | session_name on SessionRow line 112; saved_name captured line 223; restored lines 284-291; clamp fallback line 291 |

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `_set_worktrees()` | `_maybe_compute_relationships()` | `_worktrees_ready = True` then call | ✓ WIRED | Lines 177, 181 in app.py |
| `_set_terminal_sessions()` | `_maybe_compute_relationships()` | `_sessions_ready = True` then call | ✓ WIRED | Lines 187, 189 in app.py |
| `_maybe_compute_relationships()` | `_update_badges()` | call after index computed | ✓ WIRED | Line 210 in app.py |
| `_update_badges()` | `ProjectList.update_badges()` | `query_one(ProjectList).update_badges(self._rel_index)` | ✓ WIRED | Line 217 in app.py |
| `ProjectList.update_badges()` | `ProjectRow.set_counts()` | iterates self._rows | ✓ WIRED | Lines 428-431 in project_list.py |
| `compute_relationships()` | `RelationshipIndex` | pure function returns populated index | ✓ WIRED | Lines 52-109 in resolver.py |
| `set_worktrees()` | identity restore | saved_identity captured before remove_children | ✓ WIRED | Lines 312-375 in worktree_pane.py |
| `set_sessions()` | identity restore | saved_name captured before remove_children | ✓ WIRED | Lines 220-291 in terminal_pane.py |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `ProjectRow._build_content()` | `_wt_count`, `_agent_count` | `set_counts()` called from `update_badges()` | Yes — `index.worktrees_for()` returns live list from compute_relationships() which scans real worktrees | ✓ FLOWING |
| `ProjectList.update_badges()` | `index` (RelationshipIndex) | `_update_badges()` from `_maybe_compute_relationships()` | Yes — `compute_relationships(self._projects, self._current_worktrees, self._current_sessions, self._repos)` uses data from background workers | ✓ FLOWING |
| `WorktreePane.set_worktrees()` | `saved_identity` | cursor state before DOM rebuild | Yes — reads from existing `_rows` if cursor is valid | ✓ FLOWING |
| `TerminalPane.set_sessions()` | `saved_name` | cursor state before DOM rebuild | Yes — reads from existing `_rows` if cursor is valid | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| resolver imports cleanly | `python -c "from joy.resolver import compute_relationships, RelationshipIndex"` | "imports OK" | ✓ PASS |
| app imports cleanly with new fields | `python -c "from joy.app import JoyApp"` | "imports OK" | ✓ PASS |
| badge tests pass | `uv run pytest tests/test_project_list.py -x -q` | 6 passed | ✓ PASS |
| resolver tests pass | `uv run pytest tests/test_resolver.py -x -q` | 7 passed | ✓ PASS |
| cursor tests pass | `uv run pytest tests/test_worktree_pane_cursor.py tests/test_terminal_pane.py -q` | 38 passed | ✓ PASS |
| full suite clean | `uv run pytest -q` (excluding slow subset) | 260 passed, 38 deselected | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FOUND-01 | 14-01 / 14-03 | Resolver computes Project ↔ Worktree matches | ✓ SATISFIED | `compute_relationships()` implements WORKTREE (path) and BRANCH (repo+branch) matching; 3 tests verify both paths + precedence |
| FOUND-02 | 14-01 / 14-03 | Resolver computes Project ↔ Agent matches | ✓ SATISFIED | `compute_relationships()` matches AGENTS object value to `session.session_name`; test_compute_relationships_agent_by_session_name passes |
| FOUND-03 | 14-02 | WorktreePane cursor preserved by identity across DOM rebuilds | ✓ SATISFIED | `set_worktrees()` saves `(repo_name, branch)` before rebuild, restores after; 2 slow TUI tests pass |
| FOUND-04 | 14-02 | TerminalPane cursor preserved by identity across DOM rebuilds | ✓ SATISFIED | `set_sessions()` saves `session_name` before rebuild, restores after; SessionRow.session_name added; 2 slow TUI tests pass |
| BADGE-01 | 14-03 | Project rows display count of active related worktrees | ✓ SATISFIED | `ProjectRow` renders ICON_BRANCH + wt_count; set_counts() updates it; test_project_row_set_counts_updates_worktree_count passes |
| BADGE-02 | 14-03 | Project rows display count of active related agent sessions | ✓ SATISFIED | `ProjectRow` renders ICON_CLAUDE + agent_count; set_counts() updates it; test_project_row_set_counts_updates_agent_count passes |
| BADGE-03 | 14-03 | Badge counts update after each background refresh cycle | ✓ SATISFIED | Two-flag pattern in `_maybe_compute_relationships()` fires after both workers complete each cycle; flags reset before computing so every subsequent cycle updates badges |

**All 7 phase-14 requirements are covered and satisfied at the code level.**

### Anti-Patterns Found

The code review (14-REVIEW.md) identified 5 warnings and 4 info items. None block the phase goal. The most notable for verification purposes:

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/joy/app.py:218` | `except Exception: pass` in `_update_badges` — swallows all exceptions | ⚠️ Warning | Bugs in badge update path would be silent; documented in code review WR-02 |
| `src/joy/resolver.py:81-84` | Silent last-writer-wins on duplicate WORKTREE/BRANCH object | ⚠️ Warning | Two projects claiming same worktree path: second overwrites first silently; documented WR-04 |
| `src/joy/widgets/project_list.py:422` | `index: object` with `# type: ignore` — defeats static type checking | ℹ️ Info | Code review IN-01; does not break runtime behavior |
| `tests/test_project_list.py:58` | Digit-fragile assertion `"5" in content and "3" in content` | ℹ️ Info | Code review IN-02; tests still correct for current values |

None of the above are blockers — all are improvement opportunities noted for a future cleanup phase.

### Human Verification Required

#### 1. Badge Counts Visible in Live TUI

**Test:** Launch `uv run joy`, wait 2-5 seconds for first background refresh to complete. Observe all project rows in the left pane.

**Expected:** Each row shows `{project name}  [branch-icon] N  [robot-icon] M` where N = count of related worktrees, M = count of related agent sessions. Both counts are visible even when N=0 and M=0. If you have projects with active worktrees or iTerm2 sessions matching your configured AGENTS values, those counts should be non-zero.

**Why human:** Badge rendering requires a running Textual app with real iTerm2 data and git worktrees. Automating this requires spawning a live TUI.

#### 2. WorktreePane Cursor Stability Across Refresh

**Test:** In a running `joy` session, navigate WorktreePane (Tab to switch pane), move cursor down a few rows. Wait for background refresh (default 30s) or press `r` to force one.

**Expected:** Cursor stays on the same worktree after refresh — does not jump back to row 0. If the worktree you were on disappears, cursor should land near the previous position, not at the top.

**Why human:** Textual's `call_from_thread` + `remove_children` + mount timing in a live session with real background threads cannot be fully exercised in a non-running-app test context.

#### 3. TerminalPane Cursor Stability Across Refresh

**Test:** Navigate TerminalPane, move cursor to a non-first session. Trigger a refresh.

**Expected:** Cursor stays on the same session name. If the session disappears, cursor clamps near the previous position.

**Why human:** Same as above — requires live iTerm2 connection and real session data.

### Gaps Summary

No gaps. All automated truths are verified and all requirements are satisfied at the code level. The `human_needed` status reflects that Truth 4 (cursor stability in a live running app) cannot be verified programmatically without spawning a live Textual application against real iTerm2 data.

Note: The 14-03-SUMMARY.md documents that Task 3 (human verification checkpoint) was completed and approved by the developer during plan execution. This verification report notes it for completeness while flagging it as requiring fresh human confirmation if needed.

---

_Verified: 2026-04-14T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
