---
phase: 11-mr-ci-status
plan: 01
subsystem: data-fetch
tags: [gh-cli, glab-cli, subprocess, ci-status, merge-request, dataclass]

# Dependency graph
requires:
  - phase: 06-models-config-store
    provides: Repo dataclass with forge field, WorktreeInfo dataclass
provides:
  - MRInfo dataclass in models.py
  - fetch_mr_data() function returning (repo_name, branch) -> MRInfo mapping
  - GitHub fetch via gh pr list with CI status mapping
  - GitLab fetch via glab mr list + glab ci get with CI status mapping
affects: [11-02, 11-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One CLI call per repo (gh pr list, glab mr list) with Python-side branch filtering"
    - "Per-repo try/except with continue for silent error skipping (D-11)"
    - "CI status vocabulary: pass/fail/pending/None for both forges"

key-files:
  created:
    - src/joy/mr_status.py
    - tests/test_mr_status.py
  modified:
    - src/joy/models.py

key-decisions:
  - "GitLab MRs omit last_commit_hash/last_commit_msg (empty strings) to avoid O(N) per-MR API calls"
  - "GitHub uses one gh pr list call per repo with --json for all needed fields"
  - "GitLab CI requires separate glab ci get per branch since list endpoint lacks head_pipeline"

patterns-established:
  - "fetch_mr_data never raises: per-repo exceptions caught and skipped, partial results returned"
  - "CI status mapping functions normalize forge-specific values to pass/fail/pending/None"
  - "subprocess.run with check=False, timeout=15 for CLI calls"

requirements-completed: [WKTR-07, WKTR-08, WKTR-09]

# Metrics
duration: 3min
completed: 2026-04-13
---

# Phase 11 Plan 01: MR Status Data Layer Summary

**MRInfo dataclass and mr_status.py fetch module with GitHub (gh) and GitLab (glab) CLI integration for MR/PR status and CI pipeline results**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-13T13:27:50Z
- **Completed:** 2026-04-13T13:31:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- MRInfo dataclass added to models.py with 6 fields per D-08 (mr_number, is_draft, ci_status, author, last_commit_hash, last_commit_msg)
- Complete mr_status.py module with fetch_mr_data dispatching to forge-specific fetchers
- GitHub: one gh pr list call per repo, CI status mapped from statusCheckRollup
- GitLab: one glab mr list per repo + one glab ci get per branch with MR
- 30 unit tests covering all CI mapping, fetch, error handling, and integration scenarios
- Full regression suite green (254 tests passed)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED -- MRInfo dataclass and test_mr_status.py test suite** - `265a072` (test)
2. **Task 2: GREEN -- Implement mr_status.py module** - `cdca230` (feat)

## Files Created/Modified
- `src/joy/models.py` - Added MRInfo dataclass after WorktreeInfo
- `src/joy/mr_status.py` - New module: fetch_mr_data, _fetch_github_mrs, _fetch_gitlab_mrs, _fetch_glab_ci_status, _map_gh_ci_status, _map_glab_ci_status
- `tests/test_mr_status.py` - 30 tests covering all module behavior

## Decisions Made
- Followed plan exactly for all implementation decisions
- GitLab MRs use empty strings for last_commit_hash/last_commit_msg per research recommendation (avoids O(N) per-MR glab mr view calls)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- MRInfo dataclass and fetch_mr_data() are ready for integration into app.py's _load_worktrees() worker (Plan 11-02)
- WorktreeRow.build_content() can now receive MRInfo for MR-enriched row rendering (Plan 11-03)
- All tests green, no blockers

## Self-Check: PASSED

All files verified present on disk. All commit hashes found in git log.

---
*Phase: 11-mr-ci-status*
*Completed: 2026-04-13*
