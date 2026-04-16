"""ArchiveModal: three-option confirmation modal for archiving a project."""
from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from joy.models import Project


class ArchiveChoice(str, Enum):
    """The three outcomes of the archive confirmation modal."""

    ARCHIVE_WITH_CLOSE = "archive_with_close"  # Enter: archive + close terminals
    ARCHIVE_ONLY = "archive_only"              # a: archive, skip terminal close
    CANCEL = "cancel"                          # Esc: no action


class ArchiveModal(ModalScreen[ArchiveChoice]):
    """Modal to confirm archiving a project with three options.

    Enter  — Archive project and close its iTerm2 terminal sessions
    a      — Archive project only (leave terminals open)
    Escape — Cancel, do nothing
    """

    BINDINGS = [
        Binding("enter", "confirm_with_close", "Archive + close terminals"),
        Binding("a", "confirm_only", "Archive only"),
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ArchiveModal {
        align: center middle;
    }
    ArchiveModal > Vertical {
        width: 62;
        height: auto;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    ArchiveModal .modal-title {
        text-style: bold;
    }
    ArchiveModal .modal-hint {
        color: $text-muted;
    }
    """

    def __init__(self, project: Project) -> None:
        super().__init__()
        self._project = project

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Archive Project", classes="modal-title")
            yield Static(f"Archive '{self._project.name}'?")
            yield Static(
                "Worktree and terminal objects will be stripped from the archived copy.",
                classes="modal-hint",
            )
            yield Static(
                "Enter: archive + close terminals  \u00b7  a: archive only  \u00b7  Esc: cancel",
                classes="modal-hint",
            )

    def on_mount(self) -> None:
        self.focus()

    def action_confirm_with_close(self) -> None:
        """Archive the project and close its iTerm2 terminal sessions."""
        self.dismiss(ArchiveChoice.ARCHIVE_WITH_CLOSE)

    def action_confirm_only(self) -> None:
        """Archive the project without closing terminal sessions."""
        self.dismiss(ArchiveChoice.ARCHIVE_ONLY)

    def action_cancel(self) -> None:
        """Cancel — no action taken."""
        self.dismiss(ArchiveChoice.CANCEL)
