"""RepoPickerModal: select a repo to assign to a project (or clear assignment)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

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
        self._filtered: list[str | None] = list(self._options)

    def compose(self) -> ComposeResult:
        with Vertical():
            title = "Assign Repo"
            if self._current_repo:
                title += f" (current: {self._current_repo})"
            yield Static(title, classes="modal-title")
            yield Input(placeholder="Type to filter...", id="filter-input")
            yield ListView(
                *[ListItem(Label(self._label(opt))) for opt in self._options],
                id="repo-list",
            )
            yield Static("↑/↓ to navigate, Enter to select, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def _label(self, opt: str | None) -> str:
        if opt is None:
            return _NO_REPO_LABEL
        marker = " ✓" if opt == self._current_repo else ""
        return f"{opt}{marker}"

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if query:
            self._filtered = [
                opt for opt in self._options
                if (opt is not None and query in opt.lower())
                or (opt is None and query in _NO_REPO_LABEL.lower())
            ]
        else:
            self._filtered = list(self._options)
        listview = self.query_one("#repo-list", ListView)
        listview.clear()
        for opt in self._filtered:
            listview.append(ListItem(Label(self._label(opt))))

    def on_key(self, event: Key) -> None:
        """Forward up/down to ListView while filter Input has focus."""
        filter_input = self.query_one("#filter-input", Input)
        listview = self.query_one("#repo-list", ListView)
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
        """Enter in filter: auto-select if exactly 1 match, else move to list."""
        if len(self._filtered) == 1:
            self.dismiss(self._filtered[0])
        elif self._filtered:
            self.query_one("#repo-list", ListView).focus()

    def action_cancel(self) -> None:
        self.dismiss(RepoPickerModal.CANCELLED)
