---
phase: quick-260429-amk
plan: 01
subsystem: terminal-pane, hooks
tags: [claude-code, hooks, state-detection, tui]
dependency_graph:
  requires: []
  provides: [claude-state-detection, setup-hooks-cli, 3-state-terminal-indicators]
  affects: [terminal_pane, terminal_sessions, models, legend, app]
tech_stack:
  added: []
  patterns: [hook-script-ipc, tty-keyed-state-files, atomic-file-write]
key_files:
  created:
    - src/joy/hooks.py
    - tests/test_hooks.py
  modified:
    - src/joy/models.py
    - src/joy/terminal_sessions.py
    - src/joy/widgets/terminal_pane.py
    - src/joy/screens/legend.py
    - src/joy/app.py
    - tests/test_terminal_sessions.py
    - tests/test_terminal_pane.py
decisions:
  - "claude_state field on TerminalSession model replaces binary is_busy heuristic"
  - "Hook state preferred over heuristic; heuristic kept as fallback when no hook file exists"
  - "State files ignored when is_claude=False for TTY (staleness rule)"
  - "Sort order: waiting_input > busy > idle surfaces sessions needing attention first"
metrics:
  duration: 341s
  completed: 2026-04-29
  tasks_completed: 2
  tasks_total: 2
  tests_added: 20
  tests_total: 379
---

# Quick Task 260429-amk: Claude Agent Status Detection via Hooks Summary

Hook-based 3-state Claude agent detection with setup-hooks CLI, TTY-keyed JSON state files, and color-coded TerminalPane indicators (green=busy, yellow=waiting_input, dim=idle).

## Task Completion

| Task | Name | Commit(s) | Files |
|------|------|-----------|-------|
| 1 | Model + State Reader + Hook Setup | 3447b7c (RED), fbb4f67 (GREEN) | models.py, terminal_sessions.py, hooks.py, test_hooks.py, test_terminal_sessions.py |
| 2 | UI Rendering + Legend + CLI Entry Point | d49edfe | terminal_pane.py, legend.py, app.py, test_terminal_pane.py |

## What Was Built

### Hook Infrastructure (src/joy/hooks.py)
- `HOOK_SCRIPT_CONTENT`: Full bash hook script that reads Claude Code JSON from stdin, resolves TTY via process tree walk, writes atomic state files to `~/.joy/claude-states/{tty}.json`
- `HOOK_EVENTS`: 6 events -- Stop, Notification, UserPromptSubmit, PreToolUse, SessionStart, SessionEnd
- `setup_hooks()`: Installs script at `~/.joy/bin/claude-state-hook.sh` (chmod 755), merges into `~/.claude/settings.json` alongside existing hooks (e.g., terminal-notifier), creates `~/.joy/claude-states/` directory
- Idempotent: running twice produces identical settings.json

### State Reader (src/joy/terminal_sessions.py)
- `_read_claude_states()`: Reads all `~/.joy/claude-states/*.json` files into a dict keyed by TTY short name. Skips corrupt JSON and .tmp files gracefully.
- `fetch_sessions()` integration: Reads state files once per refresh cycle, populates `claude_state` on each `TerminalSession` only when `is_claude=True` (staleness rule)

### Model (src/joy/models.py)
- `TerminalSession.claude_state: str | None = None` -- values: "idle", "busy", "waiting_input", or None

### UI (src/joy/widgets/terminal_pane.py)
- `SessionRow` now accepts `claude_state` parameter instead of `is_busy`
- 3-state indicator rendering: green filled circle (busy), yellow filled circle (waiting_input), dim hollow circle (idle/None)
- Fallback: when `claude_state` is None but `is_claude=True`, uses foreground_process heuristic to derive busy/idle
- Sort order: waiting_input (0,0) > busy (0,1) > idle (0,2) > non-claude (1,x)

### Legend (src/joy/screens/legend.py)
- Added "Claude needs input" (yellow) entry between busy and idle

### CLI (src/joy/app.py)
- `joy setup-hooks` command installs hooks and prints confirmation

## Deviations from Plan

None -- plan executed exactly as written.

## TDD Gate Compliance

- RED gate: test(quick-260429-amk) commit 3447b7c -- 18 failing tests added
- GREEN gate: feat(quick-260429-amk) commit fbb4f67 -- all tests passing
- No refactor gate needed (code was clean after GREEN)

## Pre-existing Issues

- `tests/test_refresh.py::test_terminal_load_on_mount` -- was already failing before this task (verified by running on pre-change code). Not related to this change. Out of scope.

## Self-Check: PASSED
