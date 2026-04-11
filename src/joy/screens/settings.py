"""SettingsModal: overlay for editing the 5 global Config fields."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, SelectionList, Static

from joy.models import Config, PresetKind


class SettingsModal(ModalScreen[Config | None]):
    """Modal overlay for viewing and editing all 5 global Config fields.

    Returns updated Config on Save, None on Escape (D-04).
    Pre-populated with the Config values passed at construction time (Pitfall 5).
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    SettingsModal {
        align: center middle;
    }
    SettingsModal > Vertical {
        width: 70;
        height: auto;
        max-height: 80vh;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
        overflow: auto;
    }
    SettingsModal .modal-title {
        text-style: bold;
    }
    SettingsModal .field-label {
        color: $text-muted;
        margin-top: 1;
    }
    SettingsModal .modal-hint {
        color: $text-muted;
    }
    SettingsModal SelectionList {
        height: auto;
        max-height: 12;
    }
    """

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Settings", classes="modal-title")
            yield Static("IDE", classes="field-label")
            yield Input(value=self._config.ide, id="field-ide")
            yield Static("Editor", classes="field-label")
            yield Input(value=self._config.editor, id="field-editor")
            yield Static("Obsidian Vault Path", classes="field-label")
            yield Input(value=self._config.obsidian_vault, id="field-vault")
            yield Static("Terminal", classes="field-label")
            yield Input(value=self._config.terminal, id="field-terminal")
            yield Static("Default Open Kinds", classes="field-label")
            yield SelectionList(
                *[
                    (k.value, k.value, k.value in self._config.default_open_kinds)
                    for k in PresetKind
                ],
                id="field-kinds",
            )
            yield Button("Save Settings", variant="primary", id="btn-save")
            yield Static(
                "Tab to navigate, Enter / Save Settings to save, Escape to cancel",
                classes="modal-hint",
            )

    def on_mount(self) -> None:
        self.query_one("#field-ide", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._do_save()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _do_save(self) -> None:
        """Collect all field values and dismiss with updated Config (D-04)."""
        config = Config(
            ide=self.query_one("#field-ide", Input).value.strip(),
            editor=self.query_one("#field-editor", Input).value.strip(),
            obsidian_vault=self.query_one("#field-vault", Input).value.strip(),
            terminal=self.query_one("#field-terminal", Input).value.strip(),
            # Pass k.value (str) as SelectionList value param so .selected
            # returns list[str] matching Config.default_open_kinds type (T-05-01-03)
            default_open_kinds=list(
                self.query_one("#field-kinds", SelectionList).selected
            ),
        )
        self.dismiss(config)
