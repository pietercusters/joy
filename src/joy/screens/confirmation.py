"""ConfirmationModal: yes/no confirmation dialog with destructive styling."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static


class ConfirmationModal(ModalScreen[bool]):
    """Modal to confirm a destructive action.

    Shows a title, a prompt, and a hint line with destructive red border.
    Returns True on Enter, False on Escape.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
    ]

    DEFAULT_CSS = """
    ConfirmationModal {
        align: center middle;
    }
    ConfirmationModal > Vertical {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }
    ConfirmationModal .modal-title {
        text-style: bold;
    }
    ConfirmationModal .modal-hint {
        color: $text-muted;
    }
    """

    def __init__(self, title: str, prompt: str, *, hint: str = "Enter to delete, Escape to cancel") -> None:
        super().__init__()
        self._title = title
        self._prompt = prompt
        self._hint = hint

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._title, classes="modal-title")
            yield Static(self._prompt)
            yield Static(self._hint, classes="modal-hint")

    def on_mount(self) -> None:
        # Focus the screen itself since there is no Input widget
        self.focus()

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
