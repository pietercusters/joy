"""Left pane: project list widget with keyboard navigation."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView

from joy.models import Project


class ProjectList(Widget, can_focus=False):
    """Left pane: project list with keyboard navigation."""

    class ProjectHighlighted(Message):
        """Fired when highlight moves to a different project."""

        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()

    class ProjectSelected(Message):
        """Fired when user presses Enter on a project (D-04)."""

        def __init__(self, project: Project) -> None:
            self.project = project
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._projects: list[Project] = []

    def compose(self) -> ComposeResult:
        yield ListView(id="project-listview")

    def set_projects(self, projects: list[Project]) -> None:
        """Populate the list. Called from JoyApp._set_projects."""
        self._projects = projects
        listview = self.query_one("#project-listview", ListView)
        listview.clear()
        for project in projects:
            listview.append(ListItem(Label(project.name)))

    def select_first(self) -> None:
        """Auto-select the first project (PROJ-02)."""
        listview = self.query_one("#project-listview", ListView)
        if self._projects:
            listview.index = 0

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """When highlight changes, notify parent with project data."""
        if (
            event.item is not None
            and event.index is not None
            and event.index < len(self._projects)
        ):
            self.post_message(self.ProjectHighlighted(self._projects[event.index]))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """When Enter is pressed, post selection message (D-04)."""
        if (
            event.item is not None
            and event.index is not None
            and event.index < len(self._projects)
        ):
            self.post_message(self.ProjectSelected(self._projects[event.index]))
