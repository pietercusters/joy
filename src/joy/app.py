"""Entry point for the joy CLI."""
from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header

from joy.models import Project
from joy.widgets.project_detail import ProjectDetail
from joy.widgets.project_list import ProjectList


class JoyApp(App):
    """Keyboard-driven TUI for managing coding project artifacts."""

    TITLE = "joy"
    SUB_TITLE = "Projects"

    CSS = """
    #project-list { width: 1fr; }
    #project-detail { width: 2fr; }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            ProjectList(id="project-list"),
            ProjectDetail(id="project-detail"),
        )
        yield Footer()

    def on_mount(self) -> None:
        self._load_data()

    @work(thread=True)
    def _load_data(self) -> None:
        """Load projects from store in a background thread (CP-1, CP-2)."""
        from joy.store import load_projects  # noqa: PLC0415 — lazy import per CP-2

        projects = load_projects()
        self.app.call_from_thread(self._set_projects, projects)

    def _set_projects(self, projects: list[Project]) -> None:
        """Update the project list widget with loaded projects (called from thread)."""
        self._projects = projects
        self.query_one(ProjectList).set_projects(projects)
        if projects:
            self.query_one(ProjectList).select_first()

    def on_descendant_focus(self, event) -> None:
        """Update sub_title based on which pane has focus (D-08)."""
        node = event.widget
        while node is not None:
            if hasattr(node, "id"):
                if node.id == "project-detail":
                    self.sub_title = "Detail"
                    return
                if node.id in ("project-list", "project-listview"):
                    self.sub_title = "Projects"
                    return
            node = node.parent

    def on_project_list_project_highlighted(
        self, message: ProjectList.ProjectHighlighted
    ) -> None:
        """When highlight moves, update detail pane immediately."""
        self.query_one(ProjectDetail).set_project(message.project)

    def on_project_list_project_selected(
        self, message: ProjectList.ProjectSelected
    ) -> None:
        """When Enter pressed on project, update detail and shift focus (D-04)."""
        self.query_one(ProjectDetail).set_project(message.project)
        self.query_one(ProjectDetail).focus()


def main() -> None:
    """Main entry point for the joy CLI."""
    app = JoyApp()
    app.run()


if __name__ == "__main__":
    main()
