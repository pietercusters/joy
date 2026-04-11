"""ValueInputModal: single-field text input modal for object value (add or edit mode)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from joy.models import PresetKind


class ValueInputModal(ModalScreen[str | None]):
    """Modal to capture or edit an object's value.

    In add mode (existing_value=""): shows "Add {kind}", returns new value or None.
    In edit mode (existing_value set): shows "Edit {kind}", pre-populates the input.
    Returns the value string on Enter, None on Escape.
    Rejects empty strings with an error toast.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    ValueInputModal {
        align: center middle;
    }
    ValueInputModal > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    ValueInputModal .modal-title {
        text-style: bold;
    }
    ValueInputModal .modal-hint {
        color: $text-muted;
    }
    """

    def __init__(self, kind: PresetKind, existing_value: str = "") -> None:
        super().__init__()
        self._kind = kind
        self._existing_value = existing_value

    def compose(self) -> ComposeResult:
        mode = "Edit" if self._existing_value else "Add"
        hint = "Enter to save, Escape to cancel" if self._existing_value else "Enter to add, Escape to cancel"
        with Vertical():
            yield Static(f"{mode} {self._kind.value}", classes="modal-title")
            yield Input(value=self._existing_value, placeholder="Enter value")
            yield Static(hint, classes="modal-hint")

    def on_mount(self) -> None:
        inp = self.query_one(Input)
        inp.focus()
        inp.cursor_position = len(self._existing_value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            self.app.notify("Value cannot be empty", severity="error", markup=False)
            return
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)
