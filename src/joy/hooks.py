"""Claude Code hook installation and management for joy.

Provides setup_hooks() to install the state-tracking hook script and merge
it into ~/.claude/settings.json alongside any existing hooks.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOOK_EVENTS: list[str] = [
    "Stop",
    "Notification",
    "UserPromptSubmit",
    "PreToolUse",
    "SessionStart",
    "SessionEnd",
]

HOOK_COMMAND: str = "~/.joy/bin/claude-state-hook.sh"

HOOK_SCRIPT_CONTENT: str = r"""#!/bin/bash
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
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_hooks() -> None:
    """Install the Claude Code state hook script and merge into settings.json.

    Creates:
    - ~/.joy/bin/claude-state-hook.sh (executable)
    - ~/.joy/claude-states/ directory
    - Merges hook entries into ~/.claude/settings.json for all HOOK_EVENTS
    """
    home = Path.home()
    joy_dir = home / ".joy"

    _install_hook_script(joy_dir)
    _merge_settings(home / ".claude" / "settings.json")

    # Ensure state directory exists
    (joy_dir / "claude-states").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _install_hook_script(joy_dir: Path) -> Path:
    """Write the hook script to joy_dir/bin/ and make it executable.

    Args:
        joy_dir: The ~/.joy directory (accepts Path for testability).

    Returns:
        Path to the created script.
    """
    bin_dir = joy_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    script_path = bin_dir / "claude-state-hook.sh"
    script_path.write_text(HOOK_SCRIPT_CONTENT)
    os.chmod(script_path, 0o755)

    return script_path


def _merge_settings(settings_path: Path) -> None:
    """Merge joy's hook command into the Claude Code settings.json.

    For each event in HOOK_EVENTS:
    - If the event doesn't exist, create it with our hook.
    - If the event exists, find the empty-matcher group and append our hook
      (if not already present).
    - If no empty-matcher group exists, create one.

    Preserves all existing hooks (e.g., terminal-notifier).

    Args:
        settings_path: Path to ~/.claude/settings.json (accepts Path for testability).
    """
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing settings
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}

    if not isinstance(data, dict):
        data = {}

    hooks = data.setdefault("hooks", {})

    our_hook = {"type": "command", "command": HOOK_COMMAND}

    for event in HOOK_EVENTS:
        if event not in hooks:
            # Create fresh entry
            hooks[event] = [{"matcher": "", "hooks": [our_hook]}]
            continue

        groups = hooks[event]
        if not isinstance(groups, list):
            hooks[event] = [{"matcher": "", "hooks": [our_hook]}]
            continue

        # Find the empty-matcher group
        empty_group = None
        for group in groups:
            if isinstance(group, dict) and group.get("matcher", None) == "":
                empty_group = group
                break

        if empty_group is None:
            # No empty-matcher group; create one
            groups.append({"matcher": "", "hooks": [our_hook]})
        else:
            # Check if our hook is already present
            hook_list = empty_group.setdefault("hooks", [])
            already_present = any(
                isinstance(h, dict) and h.get("command") == HOOK_COMMAND
                for h in hook_list
            )
            if not already_present:
                hook_list.append(our_hook)

    # Write back
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
