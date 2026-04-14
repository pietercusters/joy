---
status: partial
phase: 13-project-workflow-settings-docs
source: [13-VERIFICATION.md]
started: 2026-04-14T13:20:00Z
updated: 2026-04-14T13:20:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Repo grouping visual
expected: Projects with repo='<name>' grouped under '<name>' header; projects without a matching repo in 'Other' group (or flat list if no registered repos)
result: [pending]

### 2. Add repo via Settings modal
expected: Repo added with auto-detected remote_url and forge. Repo name derived from directory basename. 'Added repo: <name>' notification shown.
result: [pending]

### 3. Remove repo with confirmation
expected: Repo removed from list. 'Removed repo: <name>' notification shown. Projects that referenced it now appear in 'Other' group.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
