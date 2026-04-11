---
status: partial
phase: 04-crud
source: [04-VERIFICATION.md]
started: 2026-04-11T10:30:00Z
updated: 2026-04-11T10:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Create project visual flow
expected: New project with at least one object visible in the TUI; add-object loop exits on Escape.
result: [pending]

Steps: Start `uv run joy`, press n, type a project name, Enter. Verify project appears in list and preset picker opens automatically. Add at least one object (e.g., type 'br', Enter, type 'my-branch', Enter). Press Escape. Confirm object appears in detail pane.

### 2. Edit pre-population and immediate refresh
expected: Edit modal shows existing value; change is reflected in UI immediately.
result: [pending]

Steps: With an object highlighted, press e. Verify ValueInputModal appears with the current value pre-populated and cursor at end. Change value, press Enter. Confirm update is reflected immediately in the detail pane.

### 3. Red border on destructive modals
expected: Destructive red border visible; object removed after confirmation; cursor moves to previous row.
result: [pending]

Steps: With an object highlighted, press d. Verify red-border ConfirmationModal appears with the object name. Press Escape (object stays). Press d again, then Enter (object is removed).

### 4. Adjacent selection after delete
expected: Project removed; an adjacent project becomes the selection; detail pane updates.
result: [pending]

Steps: Press Escape to return to project list. Press D on a project. Verify red-border ConfirmationModal appears with project name and warning about removing all objects. Press Enter. Confirm project is removed and adjacent project is selected.

### 5. Footer context-sensitivity
expected: Detail pane footer shows: a, e, d, n. Project list footer shows: n, D.
result: [pending]

Steps: Check footer when project list is focused vs when detail pane is focused. Verify bindings a, e, d, n, D are shown in the appropriate context.

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
