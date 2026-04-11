---
phase: quick
plan: 260411-ivh
subsystem: tui
tags: [bug-fix, uat, project-list, focus, slack]
dependency_graph:
  requires: []
  provides: [deferred-post-delete-selection, focus-aware-highlight-css, slack-url-scheme-routing]
  affects: [project_list, project_detail, operations]
tech_stack:
  added: []
  patterns: [call_after_refresh, css-focus-within, macos-url-scheme]
key_files:
  modified:
    - src/joy/widgets/project_list.py
    - src/joy/widgets/project_detail.py
    - src/joy/operations.py
decisions:
  - "Use call_after_refresh to defer post-delete list selection until after DOM rebuild"
  - "Use CSS :focus-within pseudo-class for focus-aware highlight dimming — no Python logic change"
  - "Remove -a Slack flag and rely on macOS URL handler dispatch for Slack thread deep-linking"
metrics:
  duration: "8 minutes"
  completed: "2026-04-11"
  tasks_completed: 3
  files_modified: 3
---

# Quick Fix 260411-ivh: Fix Three UAT Bugs Summary

Three targeted line-level fixes restoring post-delete selection, symmetric pane focus dimming, and Slack thread navigation.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix post-delete list selection (defer select_index) | bbee0b5 | src/joy/widgets/project_list.py |
| 2 | Fix asymmetric focus dimming (CSS :focus-within guard) | 55d8e40 | src/joy/widgets/project_detail.py |
| 3 | Fix Slack URL navigation (remove -a flag) | de4709e | src/joy/operations.py |

## What Was Done

**Task 1 — Post-delete selection timing fix:**
In `JoyListView.action_delete_project`, `parent.select_index(new_index)` was called synchronously after `parent.set_projects(projects)`. The ListView DOM rebuild (`clear()` + `append()`) had not yet been rendered, so the visual highlight was lost. Replaced with `parent.call_after_refresh(parent.select_index, new_index)` to defer until Textual processes the DOM mutations.

**Task 2 — Symmetric focus dimming:**
`ObjectRow.--highlight` was unconditionally styled with full `$accent`, so the detail-pane highlight looked identical whether the list or detail had focus. Replaced with two CSS rules: `ProjectDetail:focus-within ObjectRow.--highlight` shows full `$accent` (higher specificity wins when detail has focus), and the unscoped fallback shows `$accent 30%` (dimmed when list has focus). CSS-only change, no Python logic modified.

**Task 3 — Slack URL deep-link routing:**
`subprocess.run(["open", "-a", "Slack", url])` bypasses macOS URL handler dispatch. The `-a` flag opens the URL directly with the Slack application bundle, skipping Slack's registered `slack://` scheme handler that performs thread navigation. Removed `-a Slack` so the call routes through macOS's URL handler, identical to the generic `else` branch below it.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — the Slack branch change removes a flag and routes through the same `open` call as all other URLs. No new attack surface introduced. T-ivh-01 disposition accepted as documented in plan threat model.

## Self-Check: PASSED

- src/joy/widgets/project_list.py — modified, committed bbee0b5
- src/joy/widgets/project_detail.py — modified, committed 55d8e40
- src/joy/operations.py — modified, committed de4709e
