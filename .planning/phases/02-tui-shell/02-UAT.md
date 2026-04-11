---
status: complete
phase: 02-tui-shell
source: 02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md
started: 2026-04-11T07:00:00Z
updated: 2026-04-11T07:10:00Z
---

## Current Test

number: [testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running `joy` process. Run `uv run joy` from the repo root (or globally if installed). App launches without errors, two panes are visible, and the detail pane shows content for the first project (not blank).
result: pass

### 2. Two-Pane Layout
expected: Two panes visible side by side — narrow project list on the left (~33%), wider detail pane on the right (~67%). Project list shows all configured projects. Detail pane is never empty on startup.
result: pass

### 3. First Project Auto-Selected
expected: Without pressing any key, the first project in the list is highlighted and its objects appear in the right pane immediately on launch.
result: pass

### 4. Project List Keyboard Navigation
expected: Pressing j or ↓ moves the highlight down to the next project; k or ↑ moves it up. The detail pane updates immediately to show the newly highlighted project's objects.
result: pass

### 5. Enter Shifts Focus to Detail Pane
expected: Pressing Enter on a highlighted project moves keyboard focus to the detail pane. The detail pane shows a cursor/highlight on its first object row.
result: pass

### 6. Object Rows with Nerd Font Icons
expected: Each object in the detail pane appears on its own row with a Nerd Font icon on the left, followed by a label and value. Icons are distinct per object type (e.g., branch, URL, worktree).
result: pass

### 7. Objects Grouped with Section Headers
expected: Objects in the detail pane are grouped by type (e.g., "Worktree", "Branch", "URL"). Each group has a subtle bold header/separator above it. The groups appear in a fixed order.
result: pass

### 8. Detail Pane Cursor Navigation
expected: With focus in the detail pane, pressing j/↓ moves the highlight down to the next object row; k/↑ moves it up. The highlight is a full-width background highlight on the current row.
result: pass

### 9. Long Values Truncated
expected: Object values that are too long to fit on one line are cut off with an ellipsis (or simply clipped). Each row occupies exactly one line — no wrapping.
result: pass

### 10. Escape Returns Focus to List
expected: Pressing Escape while the detail pane is focused returns keyboard focus to the project list. j/k navigate the project list again. No key press is lost or ignored — no focus trap.
result: pass

### 11. Context-Sensitive Header Labels
expected: When the project list is focused, the header/subtitle area shows "Projects". When the detail pane is focused, it shows "Detail".
result: pass

### 12. Context-Sensitive Footer Bindings
expected: Footer binding hints change based on which pane is focused. List pane: shows up/down/enter/q hints. Detail pane: shows j/k/escape/q hints (or equivalent).
result: issue
reported: "List pane only shows q."
severity: major

### 13. Pilot Tests Pass
expected: Running `uv run pytest tests/test_tui.py -x -v` completes with all tests green. No failures, no warnings about deprecated asyncio mode.
result: pass

## Summary

total: 13
passed: 12
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Footer binding hints change based on which pane is focused. List pane shows up/down/enter/q hints."
  status: failed
  reason: "User reported: List pane only shows q."
  severity: major
  test: 12
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
