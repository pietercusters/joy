---
phase: 01-foundation
plan: "03"
subsystem: operations
tags: [subprocess, tdd, clipboard, applescript, url-dispatch, obsidian, iterm2]
dependency_graph:
  requires: ["01-01"]
  provides: ["src/joy/operations.py"]
  affects: []
tech_stack:
  added: []
  patterns:
    - "Decorator-based operation registry (_OPENERS dict keyed by ObjectType)"
    - "URL hostname-based smart dispatch for Notion and Slack"
    - "AppleScript injection prevention via ordered backslash-then-quote escaping"
    - "Subprocess list form (no shell=True) for all OS calls"
key_files:
  created:
    - src/joy/operations.py
    - tests/test_operations.py
  modified: []
decisions:
  - "Both tasks implemented in single operations.py to avoid partial state (all 6 openers in one commit)"
  - "TDD Red-Green: tests written first and committed failing, then implementation committed passing"
  - "test_all_object_types_have_opener written to cover all 6 ObjectTypes including ITERM from the start"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 01 Plan 03: Subprocess Operations Module Summary

Decorator-based dispatch registry for all 6 ObjectTypes using mocked subprocess calls for clipboard (pbcopy), browser (open), Notion/Slack app switching, Obsidian URI scheme, editor, IDE, and iTerm2 AppleScript with injection protection.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing tests for operations | 9e2b1ca | tests/test_operations.py |
| 1+2 (GREEN) | Implement operations module (all 6 openers) | eeca64b | src/joy/operations.py |

## What Was Built

### src/joy/operations.py

- `_OPENERS: dict[ObjectType, Opener]` -- registry mapping each ObjectType to its handler
- `opener(obj_type)` decorator -- registers functions as openers at module load time
- `open_object(*, item, config)` -- dispatches to the registered opener, raises ValueError if none
- `_copy_string` (STRING) -- calls `subprocess.run(["pbcopy"], input=value.encode(), check=True)`
- `_open_url` (URL) -- detects notion.so (converts to notion:// scheme), slack.com (uses open -a Slack), else plain open
- `_open_obsidian` (OBSIDIAN) -- builds `obsidian://open?vault=...&file=...` with URL-encoded components
- `_open_file` (FILE) -- calls `open -a {config.editor} {path}`
- `_open_worktree` (WORKTREE) -- calls `open -a {config.ide} {path}`
- `_open_iterm` (ITERM) -- AppleScript via osascript to create/focus named iTerm2 window

### tests/test_operations.py

15 tests covering all openers, smart URL dispatch, Obsidian URL encoding, unregistered type error, AppleScript injection prevention, complete type registry coverage, and a macos_integration-marked live iTerm2 test.

## Security: AppleScript Injection Prevention (T-1-03-01)

The iTerm2 opener escapes `\` before `"` in the window name:

```python
name = item.value.replace("\\", "\\\\").replace('"', '\\"')
```

Order matters: if `"` were escaped first, the subsequent backslash escape would corrupt the `\"` sequence. This prevents a project name like `foo" end tell; do shell script "rm -rf ~"` from injecting arbitrary AppleScript.

## Deviations from Plan

None - plan executed exactly as written.

Tasks 1 and 2 were implemented together in a single implementation commit (eeca64b) because the plan explicitly allows this approach: "If both tasks are done in a single session, write all tests upfront and implement both tasks." The RED commit contains all 15 tests; the GREEN commit contains the complete operations.py with all 6 openers.

## Known Stubs

None - all 6 openers fully wired with real subprocess calls. Config parameters are consumed (config.editor, config.ide, config.obsidian_vault). No placeholder values.

## Threat Flags

No new security surface beyond what is documented in the plan's threat model. All subprocess calls use list form (not shell=True). The one injection risk (T-1-03-01) is fully mitigated.

## Self-Check: PASSED

- [x] src/joy/operations.py created and contains all 6 openers
- [x] tests/test_operations.py created with 15 passing tests
- [x] Commit 9e2b1ca (RED tests) exists
- [x] Commit eeca64b (GREEN implementation) exists
- [x] `uv run pytest tests/ -x -q` exits 0 (50 passed)
