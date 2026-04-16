---
status: partial
phase: 17-fix-iterm2-integration-bugs-from-quick-260416-of2-remove-aut
source: [17-VERIFICATION.md]
started: 2026-04-16T18:30:00Z
updated: 2026-04-16T18:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. h-key creates tab
expected: press h on a project with no linked tab; a new iTerm2 tab appears and is linked to the project (tab_id stored)
result: [pending]

### 2. h-key activates existing tab
expected: press h on a project with a live linked tab; existing tab is focused, no duplicate tab created
result: [pending]

### 3. Stale tab notification
expected: close a project's iTerm2 tab externally, wait for session refresh; "press h to relink" notification appears in the TUI
result: [pending]

### 4. Delete closes tab
expected: delete a project that has a linked iTerm2 tab; the tab disappears from iTerm2
result: [pending]

### 5. Archive closes tab + ConfirmationModal
expected: archive a project with a linked tab; ConfirmationModal (not old ArchiveModal) appears and the tab closes in iTerm2 on confirmation
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
