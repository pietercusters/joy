"""Right pane: project detail widget (stub for Plan 02)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Static

from joy.models import Project


class ProjectDetail(Widget, can_focus=True):
    """Right pane: shows objects for the selected project. Stub for Plan 02."""

    BINDINGS = [
        Binding("escape", "focus_list", "Back"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._project: Project | None = None

    def compose(self) -> ComposeResult:
        yield Static("Select a project", id="detail-placeholder")

    def set_project(self, project: Project) -> None:
        """Update the displayed project. Plan 02 will replace this with full rendering."""
        self._project = project
        placeholder = self.query_one("#detail-placeholder", Static)
        placeholder.update(f"Project: {project.name}\n{len(project.objects)} objects")

    def action_focus_list(self) -> None:
        """Return focus to project list (D-06, CORE-04)."""
        project_list = self.app.query_one("#project-list")
        listview = project_list.query_one("#project-listview")
        listview.focus()
