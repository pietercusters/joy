---
phase: 11-mr-ci-status
verified: 2026-04-13T00:00:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run `uv run joy` with a registered GitHub or GitLab repo that has open PRs/MRs on active worktree branches. Inspect the Worktrees pane."
    expected: "Worktree rows with open MRs show !N (MR number, dimmed), an open PR icon (green) or draft icon (dim), and a CI pass/fail/pending icon on line 1. Line 2 shows @author and short commit hash (+ message for GitHub, hash only for GitLab). Worktree rows without MRs show the abbreviated path on line 2 unchanged."
    why_human: "Visual layout, icon rendering (Nerd Font glyph display vs placeholder boxes), color correctness (green/red/yellow), and line readability cannot be verified programmatically. The 11-03-SUMMARY indicates visual verification was completed and approved, but this is documented via self-report. A fresh human check confirms the fix for two bugs caught during Plan 03 (wrong commit nesting, missing GitLab sha field) is working in the live TUI."
---

# Phase 11: MR & CI Status Verification Report

**Phase Goal:** Users see open MR/PR status and CI pipeline results per worktree row, auto-detected from GitHub or GitLab
**Verified:** 2026-04-13
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Worktree rows show open MR/PR number and status badge when a merge request exists for that branch | VERIFIED | `build_content` appends `!{mr_info.mr_number}` and `ICON_MR_OPEN`/`ICON_MR_DRAFT` when `mr_info is not None` (worktree_pane.py lines 169-173). Tests: `test_build_content_mr_number_shown`, `test_build_content_mr_open_icon`, `test_build_content_mr_draft_icon` all pass. |
| 2 | Worktree rows show CI pipeline status (pass/fail/pending) when available | VERIFIED | `build_content` appends `ICON_CI_PASS`/`ICON_CI_FAIL`/`ICON_CI_PENDING` based on `mr_info.ci_status` (worktree_pane.py lines 175-180). CI slot is blank when `ci_status is None`. Tests: `test_build_content_ci_pass`, `test_build_content_ci_fail`, `test_build_content_ci_pending`, `test_build_content_ci_none_blank` all pass. |
| 3 | MR author and last commit (short hash + message) shown on second line of worktree row when MR data is available | VERIFIED | Line 2 renders `@author  hash msg` when `mr_info is not None` with author or hash, else falls back to `display_path` (worktree_pane.py lines 188-200). Tests: `test_build_content_mr_author_on_line2`, `test_build_content_mr_commit_on_line2`, `test_build_content_no_mr_path_on_line2` all pass. |

**Score:** 3/3 truths verified (automated checks)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/joy/models.py` | MRInfo dataclass with 6 fields | VERIFIED | `class MRInfo` at line 148 with `mr_number`, `is_draft`, `ci_status`, `author`, `last_commit_hash`, `last_commit_msg` |
| `src/joy/mr_status.py` | fetch_mr_data, _fetch_github_mrs, _fetch_gitlab_mrs, CI mappers | VERIFIED | All 6 functions present; 229 lines of substantive implementation with subprocess calls |
| `tests/test_mr_status.py` | 30 unit tests covering all behaviors | VERIFIED | 587 lines, 30 test functions; all pass in 0.02s |
| `src/joy/widgets/worktree_pane.py` | Extended WorktreeRow with MR rendering, ICON_MR_OPEN constant | VERIFIED | 5 new icon constants (ICON_MR_OPEN, ICON_MR_DRAFT, ICON_CI_PASS, ICON_CI_FAIL, ICON_CI_PENDING) at lines 23-27; build_content, WorktreeRow.__init__, set_worktrees, set_refresh_label all extended |
| `src/joy/app.py` | Extended _load_worktrees with fetch_mr_data | VERIFIED | `from joy.mr_status import fetch_mr_data` at line 116; `_mr_fetch_failed` state at line 64; full data pipeline wired |
| `tests/test_worktree_pane.py` | 14 new MR tests + Phase 9 regression intact | VERIFIED | 667 lines; 31 test functions; all pass in 2.00s |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/joy/mr_status.py` | `src/joy/models.py` | `from joy.models import MRInfo, Repo, WorktreeInfo` | WIRED | Line 15: `from joy.models import MRInfo, Repo, WorktreeInfo` confirmed by grep |
| `src/joy/mr_status.py` | subprocess | `subprocess.run(["gh", ...])` / `subprocess.run(["glab", ...])` | WIRED | Lines 67, 116, 160 in mr_status.py; all with `check=False, timeout=15` |
| `src/joy/app.py` | `src/joy/mr_status.py` | lazy import in `_load_worktrees` | WIRED | Line 116: `from joy.mr_status import fetch_mr_data` (lazy import inside worker method) |
| `src/joy/widgets/worktree_pane.py` | `src/joy/models.py` | `from joy.models import MRInfo, WorktreeInfo` | WIRED | Line 12: `from joy.models import MRInfo, WorktreeInfo` confirmed by grep |
| `src/joy/app.py` | `src/joy/widgets/worktree_pane.py` | `_set_worktrees` passes `mr_data` to `set_worktrees` | WIRED | Line 152-153: `await self.query_one(WorktreePane).set_worktrees(..., mr_data=mr_data)` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `worktree_pane.py` `WorktreeRow.build_content` | `mr_info: MRInfo` | `mr_data.get((wt.repo_name, wt.branch))` in `set_worktrees` | Yes — populated by `fetch_mr_data` which calls `gh pr list` / `glab mr list` subprocess | FLOWING |
| `mr_status.py` `fetch_mr_data` | `prs = json.loads(result.stdout)` | `subprocess.run(["gh", "pr", "list", ...])` | Yes — real CLI call returning JSON; `check=False, timeout=15` | FLOWING |
| `mr_status.py` `_fetch_gitlab_mrs` | `mrs = json.loads(result.stdout)` | `subprocess.run(["glab", "mr", "list", ...])` | Yes — real CLI call; `sha` field used for commit hash (bug fixed in Plan 03) | FLOWING |
| `app.py` `_load_worktrees` | `mr_data: dict` | `fetch_mr_data(repos, worktrees)` | Yes — repos and worktrees from real store/discovery | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED — requires running TUI application with authenticated gh/glab CLIs and configured repos. Cannot test without live external service state. Human verification item documents this check.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WKTR-07 | 11-01, 11-02, 11-03 | Worktree rows show open MR/PR number and status badge when MR exists | SATISFIED | `!{mr_number}` + `ICON_MR_OPEN`/`ICON_MR_DRAFT` rendered in `build_content`; 3 tests pass |
| WKTR-08 | 11-01, 11-02, 11-03 | Worktree rows show CI pipeline status (pass/fail/pending) when available | SATISFIED | `ICON_CI_PASS`/`ICON_CI_FAIL`/`ICON_CI_PENDING` in `build_content`; CI slot blank when None; `_map_gh_ci_status` and `_map_glab_ci_status` tested with 8 test cases |
| WKTR-09 | 11-01, 11-02, 11-03 | MR author and last commit (short hash + message) on line 2 when MR data available | SATISFIED | Line 2 shows `@author  hash msg` when MR present; falls back to path when absent; GitLab sha bug fixed during Plan 03 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/joy/widgets/worktree_pane.py` | 246 | `"Loading\u2026 placeholder"` (comment only) | Info | This is a docstring describing the intentional loading state widget — not a stub. The `Static("Loading\u2026")` widget is replaced by real data when `set_worktrees` is called. No impact. |

No blocking anti-patterns found.

### Human Verification Required

#### 1. Visual rendering of MR/CI badges in live TUI

**Test:** Ensure at least one repo is registered in `~/.joy/config.toml` with `forge = "github"` or `forge = "gitlab"` and has branches with open PRs/MRs as active worktrees. Run `uv run joy`. Inspect the Worktrees pane.

**Expected:**
- Rows with open MRs: Line 1 shows branch icon + branch name + `!N` (dimmed) + green PR icon (open) or dim draft icon + green check / red X / yellow dot for CI status + dirty/upstream indicators
- Rows with open MRs: Line 2 shows `@username  sha commitMsg` (GitHub) or `@username  sha` (GitLab) in dim style
- Rows without MRs: Line 1 unchanged from Phase 9 (branch + indicators only); Line 2 shows abbreviated path
- Press `r` to refresh and verify MR data updates
- Nerd Font icons display as glyphs, not placeholder boxes

**Why human:** Visual icon rendering, color accuracy (green/red/yellow), Nerd Font glyph display, and overall layout readability cannot be verified programmatically. The 11-03-SUMMARY records that visual verification was completed with two bugs caught and fixed (wrong commit nesting for GitHub, missing GitLab sha field). A confirming human check validates these fixes are live in the current codebase state.

### Gaps Summary

No gaps found. All 3 ROADMAP success criteria are verified by automated tests passing (30 mr_status tests + 31 worktree_pane tests + 268 full suite all green). The human verification item is a confirmatory visual check of already-passing automated logic, as documented by Plan 03 completion.

---

_Verified: 2026-04-13_
_Verifier: Claude (gsd-verifier)_
