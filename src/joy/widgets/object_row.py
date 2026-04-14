"""ObjectRow widget: displays a single project object as a 3-column row (icon | value | kind)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from joy.models import Config, ObjectItem, ObjectType, PresetKind

# Nerd Font icons for each preset type
PRESET_ICONS: dict[PresetKind, str] = {
    PresetKind.MR: "\ue725",       #  (nf-dev-git_merge)
    PresetKind.BRANCH: "\ue0a0",   #  (nf-pl-branch)
    PresetKind.TICKET: "\uf0ea",   #  (nf-fa-clipboard)
    PresetKind.THREAD: "\uf086",   #  (nf-fa-comment)
    PresetKind.FILE: "\uf15b",     #  (nf-fa-file)
    PresetKind.NOTE: "\uf040",     #  (nf-fa-pencil)
    PresetKind.WORKTREE: "\uf07b", #  (nf-fa-folder)
    PresetKind.AGENTS: "\uf120",   #  (nf-fa-terminal)
    PresetKind.URL: "\uf0ac",      #  (nf-fa-globe)
}


def _truncate(value: str, max_len: int = 40) -> str:
    """Truncate long values with ellipsis for toast messages."""
    return value[:37] + "..." if len(value) > max_len else value


def _success_message(item: ObjectItem, config: Config) -> str:
    """Build type-specific success toast message per D-04."""
    display = _truncate(item.label if item.label else item.value)
    match item.object_type:
        case ObjectType.STRING:
            return f"Copied: {display}"
        case ObjectType.URL:
            url = item.value
            if "notion.so" in url:
                return f"Opened in Notion: {display}"
            elif "slack.com" in url:
                return f"Opened in Slack: {display}"
            else:
                return f"Opened: {display}"
        case ObjectType.OBSIDIAN:
            return f"Opened in Obsidian: {display}"
        case ObjectType.FILE:
            return f"Opened in {config.editor}: {display}"
        case ObjectType.WORKTREE:
            return f"Opened in {config.ide}: {display}"
        case ObjectType.ITERM:
            return f"Opened in iTerm2: {display}"
        case _:
            return f"Opened: {display}"


class ObjectRow(Horizontal):
    """A single row in the detail pane: 3-column layout (icon | value | kind).

    Parent ProjectDetail manages cursor highlighting via CSS class '--highlight'.
    """

    can_focus = False

    DEFAULT_CSS = """
    ObjectRow {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }
    ObjectRow .col-icon  { width: 3; }
    ObjectRow .col-value { width: 1fr; }
    ObjectRow .col-kind  { width: 12; text-align: right; color: $text-muted; }
    """

    def __init__(self, item: ObjectItem, *, index: int = 0, **kwargs) -> None:
        self.item = item
        self.index = index
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        icon = PRESET_ICONS.get(self.item.kind, " ")
        value = self.item.label if self.item.label else self.item.value
        kind = self.item.kind.value
        yield Static(icon, classes="col-icon")
        yield Static(value, classes="col-value")
        yield Static(kind, classes="col-kind")

    def refresh_indicator(self) -> None:
        """Update the value column in-place after toggle or edit."""
        value = self.item.label if self.item.label else self.item.value
        self.query_one(".col-value", Static).update(value)
