---
status: partial
phase: 15-cross-pane-selection-sync
source: [15-VERIFICATION.md]
started: 2026-04-15T00:00:00Z
updated: 2026-04-15T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Cross-Pane Cursor Tracking (SYNC-01 through SYNC-06)
expected: Navigate any pane (ProjectList, WorktreePane, TerminalPane) and confirm the other two panes silently track cursors to related items. ProjectDetail also updates when syncing from worktree or session pane.
result: [pending]

### 2. Focus Non-Steal (SYNC-07)
expected: While navigating with j/k in any pane, keyboard focus stays on the active pane. Other panes update without stealing focus.
result: [pending]

### 3. Toggle Binding and Footer Label (SYNC-08, SYNC-09)
expected: Press x → footer shows "Sync: off", sync stops. Press x again → footer shows "Sync: on", sync resumes.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
