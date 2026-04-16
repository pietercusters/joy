---
status: diagnosed
phase: 17-fix-iterm2-integration-bugs-from-quick-260416-of2-remove-aut
source: [17-VERIFICATION.md]
started: 2026-04-16T18:30:00Z
updated: 2026-04-16T18:35:00Z
---

## Current Test

Completed human UAT. 4/5 passed. 1 gap identified.

## Tests

### 1. h-key creates tab
expected: press h on a project with no linked tab; a new iTerm2 tab appears and is linked to the project (tab_id stored)
result: FAILED — tab is created in the background but focus does not immediately shift to the new iTerm2 tab

### 2. h-key activates existing tab
expected: press h on a project with a live linked tab; existing tab is focused, no duplicate tab created
result: PASSED

### 3. Stale tab notification
expected: close a project's iTerm2 tab externally, wait for session refresh; "press h to relink" notification appears in the TUI
result: PASSED

### 4. Delete closes tab
expected: delete a project that has a linked iTerm2 tab; the tab disappears from iTerm2
result: PASSED

### 5. Archive closes tab + ConfirmationModal
expected: archive a project with a linked tab; ConfirmationModal (not old ArchiveModal) appears and the tab closes in iTerm2 on confirmation
result: PASSED

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- status: failed
  test: 1
  description: After h-key creates a new iTerm2 tab, focus does not shift to the new tab. Expected behavior is immediate focus shift to the newly created terminal tab.
  fix: After create_tab succeeds in _do_create_tab_for_project, call activate_tab (or the iTerm2 equivalent) to focus the new tab before returning.
