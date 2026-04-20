"""RepoPickerModal: select a repo to assign to a project (or clear assignment)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from joy.models import Repo

_NO_REPO_LABEL = "(none — unassign)"


class RepoPickerModal(ModalScreen[str | None]):
    """Modal to assign a project to a registered repo.

    Shows registered repos + a '(none)' option to clear the assignment.
    Returns the repo name (str) to assign, or None to unassign.
    Dismisses with the sentinel _CANCEL sentinel on Escape — callers receive
    the dismiss value and check for it via the ``cancelled`` property.

    To distinguish "user cancelled" from "user chose none":
      - Escape  → dismiss(RepoPickerModal.CANCELLED)
      - "(none)" → dismiss(None)
      - repo name → dismiss(repo.name)
    """

    CANCELLED = object()  # sentinel — caller checks ``is RepoPickerModal.CANCELLED``

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    RepoPickerModal {
        align: center middle;
    }
    RepoPickerModal > Vertical {
        width: 60;
        height: auto;
        max-height: 20;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    RepoPickerModal #repo-list {
        height: auto;
        max-height: 12;
    }
    RepoPickerModal .modal-title {
        text-style: bold;
    }
    RepoPickerModal .modal-hint {
        color: $text-muted;
    }
    """

    def __init__(self, repos: list[Repo], current_repo: str | None = None) -> None:
        super().__init__()
        self._repos = repos
        self._current_repo = current_repo
        # Options: real repos first, then unassign option
        self._options: list[str | None] = [r.name for r in repos] + [None]

    def compose(self) -> ComposeResult:
        with Vertical():
            title = "Assign Repo"
            if self._current_repo:
                title += f" (current: {self._current_repo})"
            yield Static(title, classes="modal-title")
            yield ListView(
                *[ListItem(Label(self._label(opt))) for opt in self._options],
                id="repo-list",
            )
            yield Static("↑/↓ to navigate, Enter to select, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#repo-list", ListView).focus()

    def _label(self, opt: str | None) -> str:
        if opt is None:
            return _NO_REPO_LABEL
        marker = " ✓" if opt == self._current_repo else ""
        return f"{opt}{marker}"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index is not None:
            index = event.list_view.index
            if 0 <= index < len(self._options):
                self.dismiss(self._options[index])

    def action_cancel(self) -> None:
        self.dismiss(RepoPickerModal.CANCELLED)
