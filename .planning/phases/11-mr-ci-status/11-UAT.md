---
status: complete
phase: 11-mr-ci-status
source: [11-01-SUMMARY.md, 11-02-SUMMARY.md, 11-03-SUMMARY.md]
started: 2026-04-13T14:00:00Z
updated: 2026-04-13T14:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. MR Badge on Line 1
expected: Worktree rows with open MRs show `!N` MR number, open/draft icon, and CI status icon on line 1
result: pass

### 2. CI Status Icons
expected: CI pass shows green checkmark icon, fail shows red cross icon, pending shows dot-circle icon (distinct from dirty indicator)
result: pass

### 3. Draft MR Display
expected: Draft MRs show a distinct dim icon different from the open MR icon
result: pass

### 4. Context-Sensitive Line 2
expected: Line 2 shows `@author  sha` (GitLab) or `@author  sha  commit-msg` (GitHub) when MR is present; shows abbreviated path when no MR
result: pass

### 5. No-MR Rows Unchanged
expected: Worktree rows without an open MR retain Phase 9 layout — path on line 2, no MR badge on line 1
result: pass

### 6. MR Fetch Failure Warning
expected: If MR data fetch fails entirely for a repo, border title shows an error/warning indicator
result: pass

### 7. GitLab Commit Hash on Line 2
expected: GitLab MR rows show short SHA (7 chars) from the `sha` field on line 2 alongside author
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
