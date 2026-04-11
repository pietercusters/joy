"""NameInputModal: single-field text input modal for project name."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static


class NameInputModal(ModalScreen[str | None]):
    """Modal to capture a new project name.

    Returns the project name string on Enter, None on Escape.
    Rejects empty strings with an error toast.
    Duplicate name checking is the caller's responsibility (JoyApp has _projects).
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

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("New Project", classes="modal-title")
            yield Input(placeholder="Project name")
            yield Static("Enter to create, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            self.app.notify("Project name cannot be empty", severity="error", markup=False)
            return
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)
