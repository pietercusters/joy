"""NewProjectModal: multi-field modal for creating a new project."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from joy.models import Repo

_CUSTOM_BRANCH_SENTINEL = "(type custom\u2026)"


@dataclass
class NewProjectResult:
    """Result returned by NewProjectModal when the user confirms."""

    name: str
    repo: str | None
    branch: str | None


class NewProjectModal(ModalScreen["NewProjectResult | None"]):
    """Modal that collects project name, optional repo, and optional branch.

    Returns NewProjectResult on confirmation (ctrl+n) or None on Escape.
    """

    BINDINGS = [
        ("ctrl+n", "confirm", "Create project"),
        ("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    NewProjectModal {
        align: center middle;
    }
    NewProjectModal > Vertical {
        width: 60;
        height: auto;
        max-height: 40;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    NewProjectModal .modal-title {
        text-style: bold;
    }
    NewProjectModal .section-label {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }
    NewProjectModal #repo-list {
        height: auto;
        max-height: 8;
    }
    NewProjectModal #branch-list {
        height: auto;
        max-height: 8;
    }
    NewProjectModal #branch-input {
        margin-top: 0;
    }
    NewProjectModal .modal-hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, repos: list[Repo]) -> None:
        super().__init__()
        self._repos = repos
        # Options list: repo names + None for "(none)"
        self._repo_options: list[str | None] = [r.name for r in repos] + [None]
        # Fetch recent branches
        self._branch_options: list[str] = self._fetch_recent_branches()
        # Internal state
        self._selected_repo: str | None = None
        self._selected_branch: str | None = None
        self._custom_branch_mode: bool = False

    def _fetch_recent_branches(self) -> list[str]:
        """Return up to 5 recently checked-out local branches. Returns [] on any error."""
        try:
            result = subprocess.run(
                ["git", "branch", "--sort=-committerdate", "--format=%(refname:short)"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=None,
            )
            if result.returncode != 0:
                return []
            branches = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return branches[:5]
        except Exception:
            return []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("New Project", classes="modal-title")

            # --- Name ---
            yield Static("Name", classes="section-label")
            yield Input(id="name-input", placeholder="Project name")

            # --- Repo ---
            yield Static("Repo (optional)", classes="section-label")
            yield ListView(
                *[
                    ListItem(Label(r if r is not None else "(none)"))
                    for r in self._repo_options
                ],
                id="repo-list",
            )

            # --- Branch ---
            yield Static("Branch", classes="section-label")
            branch_items = [
                ListItem(Label(b)) for b in self._branch_options
            ]
            branch_items.append(
                ListItem(Label(_CUSTOM_BRANCH_SENTINEL, markup=False), classes="branch-custom")
            )
            yield ListView(*branch_items, id="branch-list")
            yield Input(
                placeholder="Custom branch name",
                id="branch-input",
            )

            yield Static("ctrl+n to confirm, Escape to cancel", classes="modal-hint")

    def on_mount(self) -> None:
        self.query_one("#branch-input", Input).display = False
        self._custom_branch_mode = False
        self.query_one("#name-input", Input).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is None:
            return
        if event.list_view.id == "repo-list":
            if 0 <= idx < len(self._repo_options):
                self._selected_repo = self._repo_options[idx]
        elif event.list_view.id == "branch-list":
            if 0 <= idx < len(self._branch_options) + 1:
                # Check if sentinel selected
                all_options = self._branch_options + [_CUSTOM_BRANCH_SENTINEL]
                selected = all_options[idx]
                if selected == _CUSTOM_BRANCH_SENTINEL:
                    self._custom_branch_mode = True
                    self.query_one("#branch-list", ListView).display = False
                    inp = self.query_one("#branch-input", Input)
                    inp.display = True
                    inp.focus()
                else:
                    self._selected_branch = selected

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "branch-input" and self._custom_branch_mode:
            val = event.value.strip()
            self._selected_branch = val if val else None
            self.action_confirm()

    def action_confirm(self) -> None:
        name = self.query_one("#name-input", Input).value.strip()
        if not name:
            self.app.notify("Project name cannot be empty", severity="error", markup=False)
            return
        self.dismiss(NewProjectResult(name=name, repo=self._selected_repo, branch=self._selected_branch))

    def action_cancel(self) -> None:
        self.dismiss(None)
