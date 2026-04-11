"""Entry point for the joy CLI."""
from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header

from joy.models import Config, ObjectItem, Project
from joy.widgets.object_row import _success_message, _truncate
from joy.widgets.project_detail import GROUP_ORDER, ProjectDetail
from joy.widgets.project_list import ProjectList


class JoyApp(App):
    """Keyboard-driven TUI for managing coding project artifacts."""

    TITLE = "joy"
    SUB_TITLE = "Projects"

    CSS = """
    #project-list { width: 1fr; }
    #project-detail { width: 2fr; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("O", "open_all_defaults", "Open All"),
    ]

    _config: Config = Config()

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
        """Load projects and config from store in a background thread (CP-1, CP-2)."""
        from joy.store import load_config, load_projects  # noqa: PLC0415 — lazy import per CP-2

        projects = load_projects()
        config = load_config()
        self.app.call_from_thread(self._set_projects, projects, config)

    def _set_projects(self, projects: list[Project], config: Config | None = None) -> None:
        """Update the project list widget with loaded projects (called from thread)."""
        self._projects = projects
        if config is not None:
            self._config = config
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

    def action_open_all_defaults(self) -> None:
        """Open all open_by_default objects for the current project (ACT-02, D-10)."""
        detail = self.query_one(ProjectDetail)
        project = detail._project
        if project is None:
            return  # silent no-op: data not loaded yet (D-11)
        # Collect defaults in GROUP_ORDER display order (D-06)
        defaults: list[ObjectItem] = []
        for kind in GROUP_ORDER:
            for item in project.objects:
                if item.kind == kind and item.open_by_default:
                    defaults.append(item)
        if not defaults:
            return  # silent no-op: no defaults (D-11)
        self._open_defaults(defaults)

    @work(thread=True, exit_on_error=False)
    def _open_defaults(self, defaults: list[ObjectItem]) -> None:
        """Open default objects sequentially in a background thread (D-06, D-07, D-08)."""
        from joy.operations import open_object  # noqa: PLC0415
        errors: list[str] = []
        for item in defaults:
            try:
                open_object(item=item, config=self._config)
                self.app.notify(
                    _success_message(item, self._config),
                    markup=False,
                )
            except Exception:
                display = _truncate(item.label if item.label else item.value)
                errors.append(display)
        # Show accumulated error toasts at the end (D-07)
        for err in errors:
            self.app.notify(f"Failed to open: {err}", severity="error", markup=False)


def main() -> None:
    """Main entry point for the joy CLI."""
    app = JoyApp()
    app.run()


if __name__ == "__main__":
    main()
