"""Type-dispatched subprocess operations for joy objects."""
from __future__ import annotations

import subprocess
from typing import Callable
from urllib.parse import quote, urlparse

from joy.models import Config, ObjectItem, ObjectType

Opener = Callable[[ObjectItem, Config], None]
_OPENERS: dict[ObjectType, Opener] = {}


def opener(obj_type: ObjectType):
    """Register a function as the opener for an ObjectType."""
    def decorator(fn: Opener) -> Opener:
        _OPENERS[obj_type] = fn
        return fn
    return decorator


def open_object(*, item: ObjectItem, config: Config) -> None:
    """Dispatch to the registered opener for this item's object type."""
    handler = _OPENERS.get(item.object_type)
    if handler is None:
        raise ValueError(f"No opener registered for {item.object_type}")
    handler(item, config)


@opener(ObjectType.STRING)
def _copy_string(item: ObjectItem, config: Config) -> None:
    """Copy value to clipboard via pbcopy."""
    subprocess.run(["pbcopy"], input=item.value.encode("utf-8"), check=True)


@opener(ObjectType.URL)
def _open_url(item: ObjectItem, config: Config) -> None:
    """Open URL in browser, or in desktop app for Notion/Slack."""
    url = item.value
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if "notion.so" in hostname:
        notion_uri = url.replace("https://", "notion://", 1)
        subprocess.run(["open", notion_uri], check=True)
    elif "slack.com" in hostname:
        subprocess.run(["open", url], check=True)
    else:
        subprocess.run(["open", url], check=True)


@opener(ObjectType.OBSIDIAN)
def _open_obsidian(item: ObjectItem, config: Config) -> None:
    """Open file in Obsidian via obsidian:// URI scheme."""
    vault_encoded = quote(config.obsidian_vault, safe="")
    file_encoded = quote(item.value, safe="/")
    uri = f"obsidian://open?vault={vault_encoded}&file={file_encoded}"
    subprocess.run(["open", uri], check=True)


@opener(ObjectType.FILE)
def _open_file(item: ObjectItem, config: Config) -> None:
    """Open file in configured editor."""
    subprocess.run(["open", "-a", config.editor, item.value], check=True)


@opener(ObjectType.WORKTREE)
def _open_worktree(item: ObjectItem, config: Config) -> None:
    """Open worktree path in configured IDE."""
    subprocess.run(["open", "-a", config.ide, item.value], check=True)


@opener(ObjectType.ITERM)
def _open_iterm(item: ObjectItem, config: Config) -> None:
    """Create or focus a named iTerm2 window via AppleScript."""
    # Escape backslashes first, then double quotes for AppleScript string safety.
    # Order matters: reversing would double-escape the backslash in \".
    # This prevents AppleScript injection via malicious project names (T-1-03-01).
    name = item.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
    script = f'''
    tell application "iTerm2"
        activate
        set targetWindow to missing value
        repeat with w in windows
            if name of w is "{name}" then
                set targetWindow to w
                exit repeat
            end if
        end repeat
        if targetWindow is missing value then
            set targetWindow to (create window with default profile)
            tell current session of targetWindow
                set name to "{name}"
            end tell
        end if
        select targetWindow
    end tell
    '''
    subprocess.run(["osascript", "-e", script], check=True)
