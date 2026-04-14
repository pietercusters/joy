# Quick Task 260414-qk4: Summary

**Task:** bug: in the Worktree overview, when there's an MR available we should go to the MR when clicking Enter. If not, we should go to the worktree.
**Date:** 2026-04-14
**Commit:** 7ae1811

## What Was Done

Fixed `MRInfo.url` not being populated in `src/joy/mr_status.py`. The `action_activate_row` handler in `worktree_pane.py` already had the correct branching logic (open MR URL if available, otherwise open worktree in IDE), but the URL was never fetched or set.

### Changes

**`src/joy/mr_status.py`**
- GitHub: added `url` to the `--json` fields in the `gh pr list` call, and pass `url=pr.get("url", "")` to `MRInfo`
- GitLab: pass `url=mr.get("web_url", "")` to `MRInfo` (field already present in `glab mr list` JSON output)

**`tests/test_mr_status.py`**
- Added `url` field to GitHub and GitLab fixture data
- Added `assert info.url == "..."` assertions to the relevant test cases

## Result

Enter on a worktree row with an MR now opens the MR/PR in the browser. Enter on a worktree row without an MR opens the worktree in the configured IDE.
