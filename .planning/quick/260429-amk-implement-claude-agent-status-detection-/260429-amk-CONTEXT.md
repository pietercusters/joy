# Quick Task 260429-amk: Implement Claude agent status detection via hooks — Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Task Boundary

Implement Claude Code agent state detection using Claude Code hooks. Instead of screen-scraping terminal content (ccmanager approach), Claude Code reports its own state via hook events that write TTY-keyed JSON files. Joy reads these files in fetch_sessions() and displays distinct indicators in TerminalPane.

</domain>

<decisions>
## Implementation Decisions

### State Model
- 3 states: `idle` (at prompt, waiting for next user message), `busy` (thinking, executing tools), `waiting_input` (needs user approval or other input)
- Maps to existing indicator pattern but with color differentiation

### UI Indicators
- Color-coded circles reusing existing style:
  - `busy` → green ● (active/working)
  - `idle` → dim ○ (ready for input)
  - `waiting_input` → yellow/orange ● (needs attention)

### Hook Installation
- `joy setup-hooks` CLI command that reads existing ~/.claude/settings.json, merges our hooks alongside existing ones (e.g., terminal-notifier), and writes back
- Idempotent and re-runnable

### Hook Script Location
- `~/.joy/bin/claude-state-hook.sh` — joy owns ~/.joy/ directory
- `joy setup-hooks` creates the script and configures settings.json to point to it

### Hook Events
- `Stop` → idle (Claude finished turn)
- `UserPromptSubmit` → busy (user submitted prompt)
- `PreToolUse` → busy (refreshes timestamp during tool chains)
- `Notification` → waiting_input (permission prompt, idle prompt, etc.)
- `SessionStart` → idle (session started)
- `SessionEnd` → delete state file (cleanup)
- Both UserPromptSubmit AND PreToolUse used for busy state — UserPromptSubmit catches the start, PreToolUse keeps it fresh

### Staleness
- No timeout on state files — trust the file as long as is_claude=True for that TTY
- Only distrust when Claude process is gone (is_claude=False)
- SessionEnd hook deletes the file for clean exit

### TTY Linking
- Hook script walks up process tree via `ps -o tty= -p $PID` to find ancestor with real TTY (not "??")
- State file named by TTY: `~/.joy/claude-states/ttys003.json`
- Joy already reads each iTerm2 session's TTY via `session.async_get_variable("tty")`
- Direct join on TTY short name

### Scope
- Full stack: hook script + state reader in fetch_sessions + TerminalSession model + TerminalPane UI
- Complete feature, not infrastructure-only

</decisions>

<specifics>
## Specific Ideas

- Hook script is a shell script for maximum speed (no Python import overhead)
- State file format: `{"state":"idle|busy|waiting_input","session_id":"abc","ts":1234567890}`
- `_read_claude_state(tty)` function in terminal_sessions.py reads state file
- TerminalSession gets new `claude_state: str | None` field
- TerminalPane uses claude_state when available, falls back to existing is_busy heuristic
- The user's existing hooks (terminal-notifier for Stop and Notification) must be preserved — setup-hooks merges, not replaces

</specifics>

<canonical_refs>
## Canonical References

- Research conversation above: ccmanager's ClaudeStateDetector (screen-scraping approach — we chose hooks instead)
- Claude Code hooks docs: Stop, Notification, UserPromptSubmit, PreToolUse, SessionStart, SessionEnd events
- iTerm2 Python API: session.async_get_variable("tty") for TTY matching
- Existing code: src/joy/terminal_sessions.py (fetch_sessions, _detect_claude, _SHELL_PROCESSES)
- Existing code: src/joy/widgets/terminal_pane.py (SessionRow, INDICATOR_BUSY, INDICATOR_WAITING)
- Existing code: src/joy/models.py (TerminalSession dataclass)

</canonical_refs>
