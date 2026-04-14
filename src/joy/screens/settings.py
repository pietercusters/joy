"""SettingsModal: overlay for editing the 5 global Config fields plus repo management."""
from __future__ import annotations

import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, SelectionList, Static

from joy.models import Config, PresetKind, Repo, detect_forge
from joy.store import get_remote_url, save_repos, validate_repo_path


class PathInputModal(ModalScreen[str | None]):
    """Simple path input modal for adding a repo."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    DEFAULT_CSS = """
    PathInputModal { align: center middle; }
    PathInputModal > Vertical {
        width: 60; height: auto;
        background: $surface; border: thick $background 80%; padding: 1 2;
    }
    PathInputModal .modal-title { text-style: bold; }
    PathInputModal .modal-hint { color: $text-muted; }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Add Repo", classes="modal-title")
            yield Input(
                placeholder="Enter local path (e.g. /Users/you/repos/project)",
                id="path-input",
            )
            yield Static("Enter to add, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#path-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            self.app.notify("Path cannot be empty", severity="error", markup=False)
            return
        self.dismiss(value)

    def action_cancel(self) -> None:
        self.dismiss(None)


class _RepoRow(Static):
    """A single repo row in the repo list widget."""

    DEFAULT_CSS = """
    _RepoRow { width: 1fr; height: 1; padding: 0 1; }
    """

    def __init__(self, repo: Repo, **kwargs) -> None:
        self.repo = repo
        super().__init__(f"{repo.name}  {repo.local_path}", **kwargs)


class _AddRepoRequest(Message):
    """Request to add a new repo (posted by _RepoListWidget)."""


class _DeleteRepoRequest(Message):
    """Request to delete the selected repo (posted by _RepoListWidget)."""

    def __init__(self, repo: Repo) -> None:
        self.repo = repo
        super().__init__()


class _RepoListWidget(VerticalScroll, can_focus=True):
    """Focusable repo list with j/k/d/a navigation inside SettingsModal."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down"),
        Binding("up", "cursor_up", "Up"),
        Binding("a", "request_add_repo", "Add Repo", show=False),
        Binding("d", "request_delete_repo", "Delete Repo", show=False),
    ]

    DEFAULT_CSS = """
    _RepoListWidget { height: auto; max-height: 8; }
    _RepoListWidget:focus _RepoRow.--highlight { background: $accent; }
    _RepoRow.--highlight { background: $accent 30%; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cursor: int = -1
        self._rows: list[_RepoRow] = []

    def set_repos(self, repos: list[Repo]) -> None:
        """Rebuild the repo list from data."""
        self.remove_children()
        self._rows = []
        if not repos:
            self.mount(Static("  No repos registered", classes="field-label"))
            self._cursor = -1
            return
        for repo in repos:
            row = _RepoRow(repo)
            self.mount(row)
            self._rows.append(row)
        self._cursor = 0 if self._rows else -1
        self._update_highlight()

    def _update_highlight(self) -> None:
        for row in self._rows:
            row.remove_class("--highlight")
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].add_class("--highlight")

    def action_cursor_up(self) -> None:
        if self._cursor > 0:
            self._cursor -= 1
            self._update_highlight()

    def action_cursor_down(self) -> None:
        if self._cursor < len(self._rows) - 1:
            self._cursor += 1
            self._update_highlight()

    @property
    def selected_repo(self) -> Repo | None:
        if 0 <= self._cursor < len(self._rows):
            return self._rows[self._cursor].repo
        return None

    def action_request_add_repo(self) -> None:
        self.post_message(_AddRepoRequest())

    def action_request_delete_repo(self) -> None:
        repo = self.selected_repo
        if repo is not None:
            self.post_message(_DeleteRepoRequest(repo))


class SettingsModal(ModalScreen[Config | None]):
    """Modal overlay for viewing and editing all 5 global Config fields.

    Returns updated Config on Save, None on Escape (D-04).
    Pre-populated with the Config values passed at construction time (Pitfall 5).
    Also manages the repo registry (FLOW-02 D-03 through D-07).
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
        padding: 0 2 1 2;
        overflow: auto;
    }
    SettingsModal .modal-title {
        text-style: bold;
        margin-top: 1;
    }
    SettingsModal .field-label {
        color: $text-muted;
    }
    SettingsModal .modal-hint {
        color: $text-muted;
    }
    SettingsModal SelectionList {
        height: auto;
        max-height: 9;
    }
    SettingsModal Button {
        width: auto;
        margin-top: 1;
    }
    """

    def __init__(self, config: Config, repos: list[Repo] | None = None) -> None:
        super().__init__()
        self._config = config
        self._repos: list[Repo] = repos if repos is not None else []

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
            yield Static("Repos", classes="modal-title")
            yield Static(
                "j/k navigate, a to add, d to remove",
                classes="field-label",
            )
            yield _RepoListWidget(id="repo-list-widget")
            yield Button("Save Settings", variant="primary", id="btn-save")
            yield Static(
                "Tab to navigate \u00b7 Save Settings to save \u00b7 Escape to cancel",
                classes="modal-hint",
            )

    def on_mount(self) -> None:
        self.query_one("#field-ide", Input).focus()
        self.query_one("#repo-list-widget", _RepoListWidget).set_repos(self._repos)

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

    # ---- Repo management ----

    def on__add_repo_request(self, event: _AddRepoRequest) -> None:
        """Handle add-repo request from _RepoListWidget."""
        self._add_repo()

    def on__delete_repo_request(self, event: _DeleteRepoRequest) -> None:
        """Handle delete-repo request from _RepoListWidget."""
        if event.repo is None:
            return
        self._delete_repo(event.repo)

    def _add_repo(self) -> None:
        """Push PathInputModal and add repo on valid path."""

        def on_path(path: str | None) -> None:
            if path is None:
                return
            if not validate_repo_path(path):
                self.app.notify(
                    f"Path does not exist: {path}", severity="error", markup=False
                )
                return
            name = os.path.basename(path.rstrip("/"))
            if any(r.name == name for r in self._repos):
                self.app.notify(
                    f"Repo '{name}' already registered",
                    severity="error",
                    markup=False,
                )
                return
            remote_url = get_remote_url(path)
            forge = detect_forge(remote_url)
            repo = Repo(
                name=name, local_path=path, remote_url=remote_url, forge=forge
            )
            self._repos.append(repo)
            save_repos(self._repos)
            self.query_one("#repo-list-widget", _RepoListWidget).set_repos(
                self._repos
            )
            self.app.notify(f"Added repo: {name}", markup=False)

        self.app.push_screen(PathInputModal(), on_path)

    def _delete_repo(self, repo: Repo) -> None:
        """Remove a repo after confirmation via ConfirmationModal."""
        from joy.screens.confirmation import ConfirmationModal as ConfModal  # noqa: PLC0415

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            self._repos = [r for r in self._repos if r.name != repo.name]
            save_repos(self._repos)
            self.query_one("#repo-list-widget", _RepoListWidget).set_repos(
                self._repos
            )
            self.app.notify(f"Removed repo: {repo.name}", markup=False)

        self.app.push_screen(
            ConfModal(title="Remove Repo", prompt=f"Remove repo '{repo.name}'?"),
            on_confirm,
        )
