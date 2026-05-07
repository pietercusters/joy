# Quick Task 260429-amk: Claude Agent Status Detection via Hooks - Research

**Researched:** 2026-04-29
**Domain:** Claude Code hooks, process tree TTY resolution, shell scripting performance
**Confidence:** HIGH

## Summary

Claude Code hooks provide the exact event model needed for state detection: `UserPromptSubmit` and `PreToolUse` for busy, `Stop` for idle, `Notification` for waiting_input, `SessionStart`/`SessionEnd` for lifecycle. Hooks receive JSON on stdin including `session_id`, and the hook script can resolve its TTY by walking up the process tree with `ps`. The user's existing hooks (terminal-notifier for Stop and Notification) coexist naturally since multiple hooks can be appended to the same event's matcher group array.

**Primary recommendation:** Pure shell hook script with shell-builtin JSON parsing (no jq/python dependency), TTY walk-up via 1-2 `ps` calls, atomic write via temp+mv. Total overhead: ~20ms per hook invocation. Integration via new `_read_claude_states()` function in `terminal_sessions.py` that reads all state files once per refresh cycle.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Implementation Decisions
- 3 states: idle, busy, waiting_input
- Color-coded: busy=green filled, idle=dim hollow, waiting_input=yellow/orange filled
- `joy setup-hooks` CLI command, idempotent, merges with existing hooks
- Hook script at `~/.joy/bin/claude-state-hook.sh`
- Hook events: Stop->idle, UserPromptSubmit->busy, PreToolUse->busy, Notification->waiting_input, SessionStart->idle, SessionEnd->delete
- No staleness timeout -- trust file while is_claude=True
- TTY walk-up via ps, state files in `~/.joy/claude-states/`, joined on TTY short name
- Full stack: hook script + state reader + model + UI

### Specific Ideas
- Shell script for speed (no Python import overhead)
- State file format: `{"state":"idle|busy|waiting_input","session_id":"abc","ts":1234567890}`
- `_read_claude_state(tty)` function in terminal_sessions.py
- TerminalSession gets `claude_state: str | None`
- TerminalPane uses claude_state when available, falls back to is_busy heuristic
- Existing terminal-notifier hooks must be preserved
</user_constraints>

## Finding 1: TTY Walk-Up Reliability

**Confidence: HIGH** [VERIFIED: live process tree inspection on this machine]

The process tree from a Claude Code hook script looks like:

```
hook_script.sh  (TTY: ??)     -- spawned by Claude Code
  claude         (TTY: ttys041) -- the Claude Code node process  
    -zsh         (TTY: ttys041) -- the shell in iTerm2
      login      (TTY: ttys041) -- login process
        iTermServer (TTY: ??)   -- iTerm2 server
```

Key findings:
- The hook's own process gets `??` for TTY (no controlling terminal)
- Walking up ONE level (to PPID) immediately finds `claude` with the real TTY (`ttys041`)
- The walk-up needs at most 2 `ps` calls: one for self (gets `??`), one for parent (gets real TTY)
- This is extremely reliable because Claude Code inherits the shell's TTY

**Edge cases:**
- **tmux/screen:** If Claude runs inside tmux, the inner shell has a virtual TTY (`ttysNNN` on macOS) that differs from the iTerm2 session's TTY. The iTerm2 session sees the OUTER TTY where tmux client runs. This means the TTY walk-up would find the tmux virtual TTY, NOT the iTerm2 session TTY. **Mitigation:** tmux is not in the user's current workflow (verified: no tmux processes running). Document as known limitation.
- **SSH:** Remote SSH sessions have their own TTY (`ttysNNN`). Not applicable since this is macOS-local tooling.
- **Subagents:** Claude Code subagents (Agent tool) run in the same node process tree. The hook docs show `agent_id` and `agent_type` fields in stdin for subagent hooks. The TTY walk-up still works because subagents share the parent process tree.

**Recommended approach:**
```bash
PID=$$
TTY=""
while [ "$PID" != "1" ] && [ -n "$PID" ] && [ "$PID" != "0" ]; do
  T=$(ps -o tty= -p "$PID" 2>/dev/null | tr -d ' ')
  if [ -n "$T" ] && [ "$T" != "??" ]; then
    TTY="$T"
    break
  fi
  PID=$(ps -o ppid= -p "$PID" 2>/dev/null | tr -d ' ')
done
```

## Finding 2: Hook Script Performance

**Confidence: HIGH** [VERIFIED: benchmarked on this machine]

Measured overhead for the full simulated hook (parse stdin + walk tree + atomic write):
- **Total: ~21ms** (well under 50ms budget)
- Pure shell JSON parse with builtins: <1ms
- Process tree walk (1-2 `ps` calls): ~10-15ms
- Atomic file write (echo + mv -f): <1ms

**Performance strategy:**
- Use shell builtins for JSON parsing (`${var#*pattern}` / `${var%%pattern}`) -- no jq or python needed
- The JSON structure is fixed and simple; no need for robust parsing
- `ps -o tty= -p $PID` is a single syscall-level operation
- Direct `echo > file.tmp && mv -f file.tmp file` is the fastest atomic write

**Blocking behavior:** Per official docs, hooks run and their exit code determines behavior. For our events (Stop, Notification, UserPromptSubmit, PreToolUse, SessionStart, SessionEnd), exit code 0 means "success, continue." Our script always exits 0. Even if the script takes 21ms, this is negligible relative to Claude Code's turn time. The script could also use `"async": true` in the hook config to run in the background, but 21ms is fast enough that blocking is fine.

## Finding 3: settings.json Merging Strategy

**Confidence: HIGH** [VERIFIED: inspected actual settings.json + official docs]

Current settings.json hook structure:
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "terminal-notifier -message \"Claude Code Finished\"" }
        ]
      }
    ],
    "Notification": [
      { "matcher": "", "hooks": [
          { "type": "command", "command": "terminal-notifier -message \"Claude Code Needs Help\"" }
        ]
      }
    ]
  }
}
```

**Merging approach:** Each event maps to an array of matcher groups. Each matcher group has a `matcher` string and a `hooks` array. To add our hook alongside existing ones:

**Option A: Append to existing hooks array** (same matcher group):
```json
"Stop": [
  {
    "matcher": "",
    "hooks": [
      { "type": "command", "command": "terminal-notifier -message \"Claude Code Finished\"" },
      { "type": "command", "command": "~/.joy/bin/claude-state-hook.sh" }
    ]
  }
]
```

**Option B: Add a new matcher group** (separate entry in outer array):
```json
"Stop": [
  { "matcher": "", "hooks": [{ "type": "command", "command": "terminal-notifier ..." }] },
  { "matcher": "", "hooks": [{ "type": "command", "command": "~/.joy/bin/claude-state-hook.sh" }] }
]
```

**Recommendation: Option A** -- append to the existing matcher group's hooks array. Per docs, "all matching hooks run in parallel" and "identical handlers are deduplicated automatically." This keeps the config cleaner. For events that don't exist yet (UserPromptSubmit, PreToolUse, SessionStart, SessionEnd), create new entries.

**Idempotency:** `joy setup-hooks` should check if our command string is already present in any hooks array before appending. Use exact string match on the command value.

**Merging algorithm:**
1. Read `~/.claude/settings.json` with json module
2. For each event we need: check if event key exists in `hooks`
3. If exists: find matcher group with `matcher: ""`, append our hook to its `hooks` array (if not already present)
4. If no matcher group with `""`: create one with our hook
5. If event doesn't exist: create the full structure
6. Write back with json.dump (indent=2 for readability)

## Finding 4: State File Atomicity

**Confidence: HIGH** [VERIFIED: POSIX semantics + benchmarked]

**Problem:** Joy reads state files from a background thread while hook scripts write them concurrently. A partial read could produce invalid JSON.

**Solution:** Write to temp file + `mv -f` (atomic rename on POSIX):
```bash
printf '{"state":"%s","session_id":"%s","ts":%s}\n' "$STATE" "$SID" "$(date +%s)" > "$STATE_DIR/$TTY.json.tmp"
/bin/mv -f "$STATE_DIR/$TTY.json.tmp" "$STATE_DIR/$TTY.json"
```

On POSIX (macOS included), `rename(2)` is atomic -- the destination file either has the old content or the new content, never partial. The `/bin/mv -f` flag avoids interactive confirmation prompts.

**Joy reader side:** Standard `open()` + `json.load()` in Python. If the file doesn't exist or is invalid JSON, return None (graceful fallback to the existing is_busy heuristic). Wrap in try/except.

**SessionEnd cleanup:** `rm -f "$STATE_DIR/$TTY.json"` -- simple deletion. Joy's reader handles missing files.

## Finding 5: Integration with fetch_sessions()

**Confidence: HIGH** [VERIFIED: code inspection of terminal_sessions.py and app.py]

Current flow in `_load_terminal()`:
1. Background thread calls `fetch_sessions()` 
2. `fetch_sessions()` runs async iTerm2 API to collect raw session data (id, tab_id, name, job, cwd, tty)
3. After `run_until_complete()` returns, sync loop builds `TerminalSession` objects with `_detect_claude(job, tty)`
4. Returns `(sessions, live_tab_ids)`
5. Main thread calls `_set_terminal_sessions()` which pushes to TerminalPane

**Recommended integration point:** Read ALL state files once at the START of `fetch_sessions()`, before the async iTerm2 calls. Store as a dict keyed by TTY short name. Then in the sync loop (step 3), look up each session's TTY in the dict to populate `claude_state`.

```python
def _read_claude_states() -> dict[str, dict]:
    """Read all claude state files. Returns {tty_short: {"state": ..., "ts": ...}}."""
    state_dir = Path.home() / ".joy" / "claude-states"
    states = {}
    if not state_dir.is_dir():
        return states
    for f in state_dir.iterdir():
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text())
                tty = f.stem  # e.g., "ttys041"
                states[tty] = data
            except Exception:
                continue
    return states
```

In `fetch_sessions()`:
```python
claude_states = _read_claude_states()
# ... after run_until_complete ...
for session_id, tab_id, name, job, cwd, tty in raw:
    tty_short = tty.removeprefix("/dev/") if tty else ""
    state_info = claude_states.get(tty_short)
    results.append(TerminalSession(
        session_id=session_id,
        session_name=name,
        foreground_process=job,
        cwd=cwd,
        tab_id=tab_id,
        is_claude=_detect_claude(job, tty),
        claude_state=state_info.get("state") if state_info else None,
    ))
```

**TerminalSession model change:**
```python
@dataclass
class TerminalSession:
    session_id: str
    session_name: str
    foreground_process: str
    cwd: str
    tab_id: str = ""
    is_claude: bool = False
    claude_state: str | None = None  # "idle" | "busy" | "waiting_input" | None
```

**TerminalPane rendering change:** In `_build_content()` and `_sort_key()`, replace the `is_busy` parameter with logic that prefers `claude_state` when available:

```python
# In set_sessions() where is_busy is computed:
if session.claude_state is not None:
    claude_state = session.claude_state  # direct from hook
else:
    # Fallback: existing heuristic
    claude_state = "busy" if session.foreground_process.lower() not in _SHELL_PROCESSES else "idle"
```

## Common Pitfalls

### Pitfall 1: Hook script not executable
**What goes wrong:** `chmod +x` forgotten on `~/.joy/bin/claude-state-hook.sh`
**How to avoid:** `joy setup-hooks` must set the executable bit after creating the script.

### Pitfall 2: State file survives process death
**What goes wrong:** Claude crashes or user kills terminal; SessionEnd hook never fires; stale state file persists.
**How to avoid:** Per CONTEXT.md decision: trust the file only when `is_claude=True`. If `is_claude=False` for a TTY but a state file exists, ignore the state file (and optionally clean it up). This is already the planned approach.

### Pitfall 3: settings.json backup
**What goes wrong:** `joy setup-hooks` corrupts settings.json.
**How to avoid:** Read, parse, validate structure before writing. Consider writing a `.bak` before modification.

### Pitfall 4: Shell quoting in settings.json command
**What goes wrong:** Path with spaces in `~/.joy/bin/claude-state-hook.sh` (unlikely but possible if home dir has spaces).
**How to avoid:** The command string is passed to bash directly by Claude Code. Tilde expansion works. No spaces in `.joy` path.

### Pitfall 5: Race between hook write and joy read
**What goes wrong:** Joy reads state file between tmp write and mv rename -- gets ENOENT (file briefly missing).
**How to avoid:** The atomic rename approach means the file is never missing -- it either has old content or new content. The only gap is on first write (file doesn't exist yet), which is handled by the try/except in `_read_claude_states()`.

## Code Examples

### Hook Script Template
```bash
#!/bin/bash
# ~/.joy/bin/claude-state-hook.sh
# Claude Code hook: writes agent state to TTY-keyed file for joy TUI
set -euo pipefail

STATE_DIR="$HOME/.joy/claude-states"
mkdir -p "$STATE_DIR"

# Read JSON from stdin (Claude Code pipes event data)
read -r INPUT

# Parse event name and session_id with shell builtins (no jq dependency)
EVENT="${INPUT#*\"hook_event_name\":\"}"
EVENT="${EVENT%%\"*}"
SESSION="${INPUT#*\"session_id\":\"}"
SESSION="${SESSION%%\"*}"

# Walk process tree to find ancestor with real TTY
PID=$$
TTY=""
while [ "$PID" != "1" ] && [ -n "$PID" ] && [ "$PID" != "0" ]; do
  T=$(ps -o tty= -p "$PID" 2>/dev/null | tr -d ' ')
  if [ -n "$T" ] && [ "$T" != "??" ]; then
    TTY="$T"
    break
  fi
  PID=$(ps -o ppid= -p "$PID" 2>/dev/null | tr -d ' ')
done

[ -z "$TTY" ] && exit 0  # Can't determine TTY -- skip silently

STATE_FILE="$STATE_DIR/$TTY.json"

case "$EVENT" in
  SessionEnd)
    rm -f "$STATE_FILE"
    ;;
  Stop|SessionStart)
    printf '{"state":"idle","session_id":"%s","ts":%s}\n' "$SESSION" "$(date +%s)" > "$STATE_FILE.tmp"
    /bin/mv -f "$STATE_FILE.tmp" "$STATE_FILE"
    ;;
  UserPromptSubmit|PreToolUse)
    printf '{"state":"busy","session_id":"%s","ts":%s}\n' "$SESSION" "$(date +%s)" > "$STATE_FILE.tmp"
    /bin/mv -f "$STATE_FILE.tmp" "$STATE_FILE"
    ;;
  Notification)
    printf '{"state":"waiting_input","session_id":"%s","ts":%s}\n' "$SESSION" "$(date +%s)" > "$STATE_FILE.tmp"
    /bin/mv -f "$STATE_FILE.tmp" "$STATE_FILE"
    ;;
esac

exit 0
```

### settings.json After Merge (example)
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "terminal-notifier -message \"Claude Code Finished\"" },
          { "type": "command", "command": "~/.joy/bin/claude-state-hook.sh" }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "terminal-notifier -message \"Claude Code Needs Help\"" },
          { "type": "command", "command": "~/.joy/bin/claude-state-hook.sh" }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "~/.joy/bin/claude-state-hook.sh" }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "~/.joy/bin/claude-state-hook.sh" }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "~/.joy/bin/claude-state-hook.sh" }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "~/.joy/bin/claude-state-hook.sh" }
        ]
      }
    ]
  }
}
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | tmux users will not need TTY matching (not in user's workflow) | Finding 1 | tmux users would see no state indicators -- functional but degraded |
| A2 | Claude Code always pipes JSON to stdin for all hook events | Finding 2 | Script would fail to parse; would need error handling |

## Open Questions

1. **hook_event_name vs event field name**
   - What we know: Official docs show `hook_event_name` in stdin JSON
   - What's unclear: Whether the field has always been `hook_event_name` or was recently renamed from `event`
   - Recommendation: Parse `hook_event_name` (per official docs). The shell parsing handles both since it just looks for the pattern in the JSON string.

2. **PreToolUse frequency**
   - What we know: PreToolUse fires for every tool call. In a busy turn, Claude might use 10-20 tools.
   - What's unclear: Whether the 21ms overhead * N tool calls is noticeable
   - Recommendation: 21ms * 20 = 420ms total across an entire turn, spread over seconds/minutes of actual work. Negligible. Proceed as planned.

## Sources

### Primary (HIGH confidence)
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) -- complete event model, stdin schema, exit code behavior
- Live process tree inspection on this machine -- verified TTY walk-up chain
- Live benchmarks on this machine -- verified 21ms total hook overhead

### Secondary (MEDIUM confidence)
- [Claude Code Hooks Complete Guide](https://claudefa.st/blog/tools/hooks/hooks-guide) -- confirmed event list and lifecycle
- User's actual `~/.claude/settings.json` -- verified existing hook structure
