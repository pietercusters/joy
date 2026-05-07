---
phase: 260429-amk-implement-claude-agent-status-detection
reviewed: 2026-04-29T00:00:00Z
depth: quick
files_reviewed: 9
files_reviewed_list:
  - src/joy/app.py
  - src/joy/hooks.py
  - src/joy/models.py
  - src/joy/screens/legend.py
  - src/joy/terminal_sessions.py
  - src/joy/widgets/terminal_pane.py
  - tests/test_hooks.py
  - tests/test_terminal_pane.py
  - tests/test_terminal_sessions.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Code Review: Claude Agent Status Detection

**Reviewed:** 2026-04-29
**Depth:** quick (pattern scan + targeted file read for new code)
**Files Reviewed:** 9
**Status:** issues_found

## Summary

This task adds Claude Code hook-based agent state detection: a bash hook script writes TTY-keyed JSON state files, `_read_claude_states()` reads them, and `fetch_sessions()` maps them onto `TerminalSession.claude_state`. The integration flows correctly end-to-end and the test coverage is solid for the happy path. Three warnings and three info items follow.

---

## Warnings

### WR-01: Shell JSON parsing breaks on multi-line or pretty-printed input

**File:** `src/joy/hooks.py:38-40`

**Issue:** The hook script reads only **one line** from stdin (`read -r INPUT`) and then extracts `hook_event_name` and `session_id` with prefix/suffix stripping. Claude Code currently delivers a single-line JSON object, but nothing in the documented API contract guarantees this. If Claude Code ever emits pretty-printed JSON (multiple lines), `read -r` returns only the first line, `EVENT` and `SESSION` will be empty strings, and the `case` statement falls through silently — all events are dropped without error, leaving the TUI with no state updates and no diagnostic to debug from.

```bash
# Current (fragile):
read -r INPUT
EVENT="${INPUT#*\"hook_event_name\":\"}"
EVENT="${EVENT%%\"*}"
```

The `.tmp` → `mv` atomicity is good, but a silent empty-EVENT case writes nothing, which means stale state lingers. Consider reading all stdin and guarding against empty parses:

```bash
INPUT=$(cat)
EVENT="${INPUT#*\"hook_event_name\":\"}"
EVENT="${EVENT%%\"*}"
SESSION="${INPUT#*\"session_id\":\"}"
SESSION="${SESSION%%\"*}"

# Guard: if parse failed, exit cleanly
[ -z "$EVENT" ] && exit 0
```

---

### WR-02: TTY walk-up loop can produce a path-containing TTY value in the filename

**File:** `src/joy/hooks.py:47-58`

**Issue:** The TTY value returned by `ps -o tty=` is a **short** device name like `ttys041` on macOS. However, on Linux (or in unusual macOS environments) it can be a full path like `/dev/pts/3`. The script uses this value directly as the filename stem:

```bash
STATE_FILE="$STATE_DIR/$TTY.json"
```

If `TTY` contains a slash (e.g., `pts/3`), the write attempts `~/.joy/claude-states/pts/3.json`, which requires an intermediate directory `pts/` that does not exist, causing `printf ... > "$STATE_FILE.tmp"` to fail with a non-zero exit that aborts the script (`set -euo pipefail`). This is not a macOS risk today but could also surface if `ps -o tty=` on a particular macOS version returns a `/dev/` prefix.

The Python reader already sanitizes the prefix via `tty.removeprefix("/dev/")`, so the fix is to normalize in the shell too:

```bash
TTY="${TTY#/dev/}"       # strip /dev/ prefix if present
TTY="${TTY//\//-}"       # replace any remaining slashes with dash
STATE_FILE="$STATE_DIR/$TTY.json"
```

---

### WR-03: `_read_claude_states` silently ignores non-dict JSON values

**File:** `src/joy/terminal_sessions.py:25-30`

**Issue:** `json.loads(f.read_text())` may return a non-dict value (list, string, number) for a malformed-but-valid JSON file. The result is stored in `states[tty]` without a type check. Downstream, `state_info.get("state")` is called on whatever was stored — if it is a list or string this raises `AttributeError`, which is caught by the outer `except Exception: continue` in the loop... but wait, the type check exception would actually happen in `fetch_sessions()` at line 132, **outside** the `_read_claude_states` try/except. At that point there is no catch, so a `AttributeError` on `state_info.get("state")` would propagate to `fetch_sessions()` and cause the entire function to return `None`, dropping all session data for that refresh cycle.

**Fix:** Add a type guard when storing the parsed data:

```python
data = json.loads(f.read_text())
if not isinstance(data, dict):
    continue
tty = f.stem
states[tty] = data
```

---

## Info

### IN-01: `INDICATOR_WAITING_INPUT` is the same codepoint as `INDICATOR_BUSY`

**File:** `src/joy/widgets/terminal_pane.py:30-31`

**Issue:** Both constants resolve to `\u25cf` (BLACK CIRCLE). The only visual differentiation is the Rich style applied at render time (`style="green"` vs `style="yellow"`). This is intentional and correct, but the comment on line 30 says "BLACK CIRCLE -- session running claude" while line 31 lacks a similar clarification. A reader inspecting the constants sees two identical values and may assume the second is redundant. A brief comment would clarify:

```python
INDICATOR_BUSY          = "\u25cf"  # BLACK CIRCLE green -- claude running
INDICATOR_WAITING_INPUT = "\u25cf"  # BLACK CIRCLE yellow -- claude awaiting user
```

---

### IN-02: No test for corrupt `settings.json` (non-dict root)

**File:** `tests/test_hooks.py`

**Issue:** `_merge_settings` handles a corrupt JSON file (via the `except json.JSONDecodeError` branch) and a non-dict root (via `if not isinstance(data, dict): data = {}`), but neither path is covered by a test. A regression here would silently overwrite a user's `settings.json` with only joy's hooks. Worth adding one test:

```python
def test_setup_hooks_handles_corrupt_settings(self, fake_home):
    settings_path = fake_home / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("NOT JSON {{{")
    setup_hooks()
    data = json.loads(settings_path.read_text())
    assert "hooks" in data  # should not crash, should produce valid output
```

---

### IN-03: No test for empty `SESSION` in hook script (parse failure path)

**File:** `tests/test_hooks.py`

**Issue:** There is no test that verifies the hook script's behaviour when `session_id` is absent from the stdin JSON. The current shell parsing silently produces an empty `SESSION` string, which gets written into the JSON file as `"session_id":""`. This is benign but untested. The broader concern (noted in WR-01) is also untested: what happens when the input spans multiple lines? A single integration-level test using `subprocess` to invoke the installed script with controlled stdin would surface both issues.

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: quick_
