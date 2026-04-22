"""ObjectRow widget: displays a single project object as a 3-column row (icon | value | kind)."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from joy.models import Config, ObjectItem, ObjectType, PresetKind

# Global shortcut keys for each kind (shown as hints on rows)
KIND_SHORTCUT: dict[PresetKind, str] = {
    PresetKind.BRANCH: "b",
    PresetKind.MR: "m",
    PresetKind.WORKTREE: "i",
    PresetKind.TICKET: "y",
    PresetKind.NOTE: "u",
    PresetKind.THREAD: "t",
    PresetKind.TERMINALS: "h",
    PresetKind.REPO: "r",
}

# Nerd Font icons for each preset type
PRESET_ICONS: dict[PresetKind, str] = {
    PresetKind.MR: "\ue725",       #  (nf-dev-git_merge)
    PresetKind.BRANCH: "\ue0a0",   #  (nf-pl-branch)
    PresetKind.TICKET: "\uf0ea",   #  (nf-fa-clipboard)
    PresetKind.THREAD: "\uf086",   #  (nf-fa-comment)
    PresetKind.FILE: "\uf15b",     #  (nf-fa-file)
    PresetKind.NOTE: "\uf040",     #  (nf-fa-pencil)
    PresetKind.WORKTREE: "\uf07b", #  (nf-fa-folder)
    PresetKind.TERMINALS: "\uf120",   #  (nf-fa-terminal)
    PresetKind.URL: "\uf0ac",      #  (nf-fa-globe)
    PresetKind.REPO: "\uf401",     #  (nf-oct-repo)
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

    The icon column contains a dot indicator (open_by_default) and the preset icon.
    The value column fills remaining space and wraps if needed.
    The kind column is fixed-width and right-aligned.
    Parent ProjectDetail manages cursor highlighting via CSS class '--highlight'.
    """

    can_focus = False

    DEFAULT_CSS = """
    ObjectRow {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }
    ObjectRow .col-icon  { width: 5; }
    ObjectRow .col-value { width: 1fr; }
    ObjectRow .col-kind  { width: 12; text-align: right; color: $text-muted; }
    ObjectRow .col-shortcut { width: 5; text-align: right; color: $text-muted; }
    """

    def __init__(self, item: ObjectItem, *, index: int = 0, show_shortcut: bool = False, **kwargs) -> None:
        self.item = item
        self.index = index
        self.show_shortcut = show_shortcut
        super().__init__(**kwargs)

    @staticmethod
    def _build_icon_text(item: ObjectItem) -> Text:
        """Build the icon column Text: dot indicator + preset icon."""
        dot = "\u25cf" if item.open_by_default else "\u25cb"
        dot_style = "bright_white" if item.open_by_default else "grey50"
        icon = PRESET_ICONS.get(item.kind, " ")
        t = Text()
        t.append(dot, style=dot_style)
        t.append(f" {icon}")
        return t

    def compose(self) -> ComposeResult:
        value = self.item.label if self.item.label else self.item.value
        kind = self.item.kind.value
        shortcut = KIND_SHORTCUT.get(self.item.kind)
        hint: Text
        if self.show_shortcut and shortcut:
            hint = Text(f"[{shortcut}]")  # Text bypasses Rich markup parsing
        else:
            hint = Text("")
        yield Static(self._build_icon_text(self.item), classes="col-icon")
        yield Static(value, classes="col-value")
        yield Static(kind, classes="col-kind")
        yield Static(hint, classes="col-shortcut")

    def refresh_indicator(self) -> None:
        """Update icon and value columns in-place after toggle or edit."""
        value = self.item.label if self.item.label else self.item.value
        self.query_one(".col-icon", Static).update(self._build_icon_text(self.item))
        self.query_one(".col-value", Static).update(value)
