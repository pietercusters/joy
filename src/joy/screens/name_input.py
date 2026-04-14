"""NameInputModal: single-field text input modal for project name."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static


class NameInputModal(ModalScreen[str | None]):
    """Modal to capture a text value (project name, branch filter, etc.).

    Returns the entered string on Enter, None on Escape.
    Rejects empty strings with an error toast.
    Duplicate name checking is the caller's responsibility.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    NameInputModal {
        align: center middle;
    }
    NameInputModal > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    NameInputModal .modal-title {
        text-style: bold;
    }
    NameInputModal .modal-hint {
        color: $text-muted;
    }
    """

    def __init__(
        self,
        *,
        title: str = "New Project",
        initial_value: str = "",
        placeholder: str = "Project name",
        hint: str = "Enter to confirm, Escape to cancel",
    ) -> None:
        super().__init__()
        self._title = title
        self._initial_value = initial_value
        self._placeholder = placeholder
        self._hint = hint

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._title, classes="modal-title")
            yield Input(value=self._initial_value, placeholder=self._placeholder)
            yield Static(self._hint, classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            self.app.notify("Value cannot be empty", severity="error", markup=False)
            return
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)
