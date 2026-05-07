---
status: complete
quick_id: 260506-rc1
date: 2026-05-06
---

# Quick Task 260506-rc1: Add MR pane + placeholder pane

## What was done

### Task 1: Data model + mr_status.py refactor (df6cacc)
- Added `MRDetail` dataclass to `models.py` with title, review_status, repo_name, branch, is_review_request fields
- Added `BatchMRResult` dataclass to `mr_status.py` with by_branch, authored, review_requests fields
- Refactored `fetch_mr_data` to return `BatchMRResult` with batch author/reviewer queries
- Added per-branch fallback for worktree branches missing from batch results
- Added review status mapping for GitHub (`reviewDecision`) and GitLab (`detailed_merge_status`)
- Added review status icons to `icons.py`
- 50+ new tests covering authored MRs, review requests, status mapping, and per-branch fallback

### Task 2: MR pane widget, placeholder pane, 3x2 grid (255bf59)
- Created `MRPane` widget with two sections (My MRs / Review Requests), cursor navigation, and Enter to open MR URL
- Created `PlaceholderPane` (non-focusable, skipped by Tab)
- Expanded grid from 2x2 to 3x2 (3 columns, 2 rows)
- Wired `BatchMRResult` from background worker through to MR pane via `set_mr_data()`
- Updated `_PANE_HINTS`, `on_descendant_focus`, refresh labels for new panes
- Updated `test_pane_layout.py` for 6-pane assertions and 5-pane Tab cycling

### Task 3: Integration regression verification
- Full test suite: 388 passed, 11 failed (all pre-existing), 36 deselected
- No new test failures introduced
- Worktree pane MR badges preserved (backward compatible via `by_branch` dict)

## Files changed

| File | Change |
|------|--------|
| src/joy/models.py | Added MRDetail dataclass |
| src/joy/mr_status.py | BatchMRResult, batch fetching, per-branch fallback, review status |
| src/joy/widgets/icons.py | Review status icons |
| src/joy/widgets/mr_pane.py | New MR pane widget |
| src/joy/widgets/placeholder_pane.py | New placeholder pane widget |
| src/joy/widgets/__init__.py | Exports for new widgets |
| src/joy/app.py | 3x2 grid, MR pane wiring, BatchMRResult handling |
| tests/test_mr_status.py | 50+ new tests for batch fetching and review status |
| tests/test_mr_pane.py | New tests for MR pane widget |
| tests/test_pane_layout.py | Updated for 6-pane layout |
