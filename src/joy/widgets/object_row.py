"""ObjectRow widget: displays a single project object with icon, label, and value."""
from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from joy.models import ObjectItem, PresetKind

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


class ObjectRow(Static):
    """A single row in the detail pane: icon + preset label + value.

    Rows are single-height and truncated at the boundary (overflow: hidden).
    Parent ProjectDetail manages cursor highlighting via CSS class '--highlight'.
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
        """Build the display text: icon  label  value, truncated with ellipsis."""
        icon = PRESET_ICONS.get(item.kind, " ")
        label = item.kind.value
        value = item.label if item.label else item.value
        return Text(f"{icon}  {label}  {value}", no_wrap=True, overflow="ellipsis")
