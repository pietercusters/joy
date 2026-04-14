"""PresetPickerModal: type-to-filter modal for selecting a PresetKind."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from joy.models import PresetKind
from joy.widgets.object_row import PRESET_ICONS
from joy.widgets.project_detail import SEMANTIC_GROUPS

# Flatten SEMANTIC_GROUPS into a single list of user-addable preset kinds.
# REPO is excluded since it is synthesized from project.repo, not user-added.
_ALL_PRESETS: list[PresetKind] = [
    kind for _label, kinds in SEMANTIC_GROUPS for kind in kinds if kind != PresetKind.REPO
]


class PresetPickerModal(ModalScreen[PresetKind | None]):
    """Modal to select a preset kind via type-to-filter.

    Displays all user-addable PresetKind values in SEMANTIC_GROUPS order.
    Filters in real-time as user types. Up/down arrows navigate the list while typing.
    Returns selected PresetKind on Enter, None on Escape.
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

    def __init__(self) -> None:
        super().__init__()
        self._filtered: list[PresetKind] = list(self.ALL_PRESETS)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Add Object", classes="modal-title")
            yield Input(placeholder="Type to filter...", id="filter-input")
            yield ListView(
                *[
                    ListItem(Label(f"{PRESET_ICONS[k]}  {k.value}"))
                    for k in self.ALL_PRESETS
                ],
                id="preset-list",
            )
            yield Static("↑/↓ to navigate, Enter to select, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        self._filtered = [k for k in self.ALL_PRESETS if query in k.value.lower()]
        listview = self.query_one("#preset-list", ListView)
        listview.clear()
        for kind in self._filtered:
            listview.append(ListItem(Label(f"{PRESET_ICONS[kind]}  {kind.value}")))

    def on_key(self, event: Key) -> None:
        """Intercept up/down to navigate the ListView while the filter Input has focus.

        The Input widget captures all key events, so arrow keys would normally be
        consumed for cursor movement within the input. We intercept them here and
        forward them to the ListView so the user can navigate the list while typing.
        """
        filter_input = self.query_one("#filter-input", Input)
        listview = self.query_one("#preset-list", ListView)
        if filter_input.has_focus:
            if event.key == "down":
                event.prevent_default()
                event.stop()
                listview.action_cursor_down()
            elif event.key == "up":
                event.prevent_default()
                event.stop()
                listview.action_cursor_up()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if self._filtered and event.list_view.index is not None:
            index = event.list_view.index
            if 0 <= index < len(self._filtered):
                self.dismiss(self._filtered[index])

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter in filter input: if exactly 1 match dismiss with it; else move focus to list."""
        if len(self._filtered) == 1:
            self.dismiss(self._filtered[0])
        elif self._filtered:
            listview = self.query_one("#preset-list", ListView)
            listview.focus()

    def action_cancel(self) -> None:
        self.dismiss(None)
