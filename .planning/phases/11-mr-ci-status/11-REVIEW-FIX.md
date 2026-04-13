---
phase: 11-mr-ci-status
fixed_at: 2026-04-13T14:35:02Z
review_path: .planning/phases/11-mr-ci-status/11-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-04-13T14:35:02Z
**Source review:** .planning/phases/11-mr-ci-status/11-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: False-positive MR failure flag when repos have no open MRs

**Files modified:** `src/joy/app.py`
**Commit:** 0ed83d7
**Applied fix:** Removed the `forgeable and worktrees and not mr_data` heuristic from `_load_worktrees`. The inner try block now only sets `mr_failed = True` via the `except Exception` path, not from an empty-dict inference. An empty `mr_data` result is the normal state for repos with no open MRs.

### WR-02: Unguarded key access on `author` field in GitHub PR fetch

**Files modified:** `src/joy/mr_status.py`
**Commit:** 86870d7
**Applied fix:** Applied guard pattern at both call sites. In `_fetch_github_mrs` (line 95): `author_obj = pr.get("author") or {}` with `author_obj.get('login', 'unknown')`. In `_fetch_gitlab_mrs` (line 144): `author_obj = mr.get("author") or {}` with `author_obj.get('username', 'unknown')`. Both guard against `None` author (deleted accounts, bots, external contributors) that would have caused a `TypeError` silently swallowed by the outer `except Exception`.

### WR-03: `mr_error=True` silently suppresses stale indicator

**Files modified:** `src/joy/widgets/worktree_pane.py`
**Commit:** 0fa0bf2
**Applied fix:** Rewrote `set_refresh_label` to build `border_title` from a parts list. The warning icon is now appended when either `stale` or `mr_error` is True; "mr fetch failed" is appended when `mr_error` is True; `timestamp` is always last. When both flags are active the output combines all indicators (e.g. `"Worktrees  ⚠  mr fetch failed  2m ago"`).

---

_Fixed: 2026-04-13T14:35:02Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
