---
phase: 11-mr-ci-status
plan: 03
type: checkpoint
status: verified

key-files:
  verified: []

decisions: []
---

# Summary

Visual verification of Phase 11 MR & CI Status rendering in the live TUI. User confirmed correct rendering.

## What Was Verified

- MR badges render on line 1: `!N`, open/draft icon, CI pass/fail/pending icon
- Line 2 shows `@author  sha` (GitLab) or `@author  sha  commit-msg` (GitHub) instead of path
- Worktree rows without MRs retain Phase 9 layout (path on line 2)
- Nerd Font icons display correctly

## Issues Found and Fixed During Verification

Two bugs were caught and fixed during visual inspection:

1. **Wrong nested commit lookup** — initial fix incorrectly added `.get("commit", {})` nesting for GitHub. Reverted; `gh pr list --json commits` returns flat objects with `oid`/`messageHeadline` at top level.

2. **GitLab commit hash missing** — `_fetch_gitlab_mrs` set `last_commit_hash=""` assuming unavailability, but `glab mr list --output json` includes a `sha` field (latest commit SHA). Fixed to use `mr["sha"][:7]`. Line 2 now shows author + short hash for GitLab MRs.

## Self-Check: PASSED
