---
status: partial
phase: 17-fix-iterm2-integration-bugs-from-quick-260416-of2-remove-aut
source: [17-VERIFICATION.md]
started: 2026-04-16T18:30:00Z
updated: 2026-04-16T00:00:00Z
---

## Current Test

Gap closure complete (Plan 17-03). Re-verification required for test 1 (h-key focus) and regression checks 2-5.

## Tests

### 1. h-key creates tab and focuses it
expected: press h on a project with no linked tab; a new iTerm2 tab appears, is linked to the project (tab_id stored), AND focus shifts immediately to the new tab
result: [pending re-verification after gap closure in Plan 17-03]

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
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

- status: resolved
  test: 1
  description: After h-key creates a new iTerm2 tab, focus did not shift to the new tab.
  fix: Plan 17-03 added await tab.async_select() + await app.async_activate() inside create_tab. Needs live re-verification.
