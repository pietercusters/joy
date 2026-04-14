"""ObjectRow widget: displays a single project object with icon, label, and value."""
from __future__ import annotations

from rich.text import Text
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


class ObjectRow(Static):
    """A single row in the detail pane: dot + icon + preset label + value.

    Rows are single-height and truncated at the boundary (overflow: hidden).
    Parent ProjectDetail manages cursor highlighting via CSS class '--highlight'.
    The dot indicator (U+25CF filled / U+25CB empty) reflects open_by_default status (D-01, D-02).
    """

    can_focus = False

    DEFAULT_CSS = """
    ObjectRow {
        width: 1fr;
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(self, item: ObjectItem, *, index: int = 0, **kwargs) -> None:
        self.item = item
        self.index = index
        renderable = self._render_text(item)
        super().__init__(renderable, **kwargs)

    @staticmethod
    def _render_text(item: ObjectItem) -> Text:
        """Build display text: dot  icon  label  value (per D-01, D-02)."""
        dot = "\u25cf" if item.open_by_default else "\u25cb"  # filled or empty circle
        dot_style = "bright_white" if item.open_by_default else "grey50"
        icon = PRESET_ICONS.get(item.kind, " ")
        label = item.kind.value
        value = item.label if item.label else item.value
        t = Text(no_wrap=True, overflow="ellipsis")
        t.append(dot, style=dot_style)
        t.append(f" {icon}  {label}  {value}")
        return t

    def refresh_indicator(self) -> None:
        """Rebuild and update the row's rendered text in-place after toggle."""
        self.update(self._render_text(self.item))
