"""PresetPickerModal: list-only modal for selecting a PresetKind."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from joy.models import PresetKind
from joy.widgets.object_row import PRESET_ICONS
from joy.widgets.project_detail import SEMANTIC_GROUPS

# Flatten SEMANTIC_GROUPS into a single list of user-addable preset kinds.
# REPO is excluded since it is synthesized from project.repo, not user-added.
_ALL_PRESETS: list[PresetKind] = [
    kind for _label, kinds in SEMANTIC_GROUPS for kind in kinds if kind != PresetKind.REPO
]


class PresetPickerModal(ModalScreen[PresetKind | None]):
    """Modal to select a preset kind from a list.

    Displays all user-addable PresetKind values in SEMANTIC_GROUPS order.
    Up/down arrows navigate the list. Returns selected PresetKind on Enter,
    None on Escape.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    ALL_PRESETS: list[PresetKind] = list(_ALL_PRESETS)

    DEFAULT_CSS = """
    PresetPickerModal {
        align: center middle;
    }
    PresetPickerModal > Vertical {
        width: 60;
        height: auto;
        max-height: 20;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    PresetPickerModal #preset-list {
        height: auto;
        max-height: 12;
    }
    PresetPickerModal .modal-title {
        text-style: bold;
    }
    PresetPickerModal .modal-hint {
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Add Object", classes="modal-title")
            yield ListView(
                *[
                    ListItem(Label(f"{PRESET_ICONS[k]}  {k.value}"))
                    for k in self.ALL_PRESETS
                ],
                id="preset-list",
            )
            yield Static("↑/↓ to navigate, Enter to select, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#preset-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index is not None:
            index = event.list_view.index
            if 0 <= index < len(self.ALL_PRESETS):
                self.dismiss(self.ALL_PRESETS[index])

    def action_cancel(self) -> None:
        self.dismiss(None)
