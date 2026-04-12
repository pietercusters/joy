"""Left pane: project list widget with keyboard navigation."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView

from joy.models import Project


class JoyListView(ListView):
    """ListView subclass that adds vim-style j/k navigation."""

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("enter", "select_cursor", "Open"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("D", "delete_project", "Delete", show=True),
        Binding("delete", "delete_project", "Delete", show=False),
        Binding("/", "filter", "Filter", show=True),
    ]

    _filter_active: bool = False

    def action_filter(self) -> None:
        """Enter filter mode: mount Input above the list (D-06)."""
        if self._filter_active:
            return  # already in filter mode -- no-op (prevent duplicate mount)
        parent = self.app.query_one("#project-list", ProjectList)
        parent._is_filtered = False  # clear any Enter-kept filter state
        filter_input = Input(placeholder="Filter projects...", id="filter-input")
        parent.mount(filter_input, before=self)
        self._filter_active = True
        filter_input.focus()

    def action_delete_project(self) -> None:
        """Delete the highlighted project after confirmation (PROJ-05, D-12, D-13)."""
        from joy.screens import ConfirmationModal  # noqa: PLC0415 — lazy import avoids circular dep
        parent = self.app.query_one("#project-list", ProjectList)
        index = self.index
        if index is None or index >= len(parent._projects):
            return
        project = parent._projects[index]

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            projects = self.app._projects
            try:
                projects.remove(project)
            except ValueError:
                return  # already removed
            self.app._save_projects_bg()
            parent.set_projects(projects)
            if projects:
                # Select adjacent: next if available, else previous (D-13).
                # clear()+append() in set_projects are synchronous DOM mutations,
                # so focus and index can be restored immediately after.
                new_index = min(index, len(projects) - 1)
                self.focus()           # restore keyboard focus lost when clear() ran
                self.index = new_index  # restore visual highlight on adjacent item
            else:
                # No projects left — clear detail pane
                from joy.widgets.project_detail import ProjectDetail  # noqa: PLC0415
                detail = self.app.query_one("#project-detail", ProjectDetail)
                detail._project = None
                detail._rows = []
                detail._cursor = -1
                scroll = detail.query_one("#detail-scroll")
                scroll.remove_children()
            self.app.notify(f"Deleted project: '{project.name}'", markup=False)

        self.app.push_screen(
            ConfirmationModal(
                title="Delete Project",
                prompt=f"Delete project '{project.name}'? This will remove it and all its objects.",
            ),
            on_confirm,
        )


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
        self._is_filtered: bool = False

    def compose(self) -> ComposeResult:
        yield JoyListView(id="project-listview")

    def set_projects(self, projects: list[Project]) -> None:
        """Populate the list. Called from JoyApp._set_projects."""
        self._projects = projects
        listview = self.query_one("#project-listview", JoyListView)
        listview.clear()
        for project in projects:
            listview.append(ListItem(Label(project.name)))

    def select_first(self) -> None:
        """Auto-select the first project (PROJ-02)."""
        listview = self.query_one("#project-listview", JoyListView)
        if self._projects:
            listview.index = 0

    def select_index(self, index: int) -> None:
        """Select project at given index."""
        listview = self.query_one("#project-listview", JoyListView)
        if 0 <= index < len(self._projects):
            listview.index = index

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter project list in real-time as user types (D-07)."""
        query = event.value.lower()
        if query:
            filtered = [p for p in self.app._projects if query in p.name.lower()]
        else:
            filtered = list(self.app._projects)  # empty string = full list (D-08)
        self.set_projects(filtered)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter in filter input: dismiss filter, keep current subset (D-08)."""
        self._exit_filter_mode(restore=False)
        self._is_filtered = True  # list is still filtered; Escape will restore

    def on_key(self, event) -> None:
        """Handle Escape to exit filter mode without conflicting with modals (Pitfall 1)."""
        listview = self.query_one("#project-listview", JoyListView)
        if event.key == "escape" and (listview._filter_active or self._is_filtered):
            event.stop()
            self._exit_filter_mode(restore=True)

    def _exit_filter_mode(self, *, restore: bool = True) -> None:
        """Remove filter Input and optionally restore full project list (D-08, D-09)."""
        listview = self.query_one("#project-listview", JoyListView)
        try:
            filter_input = self.query_one("#filter-input", Input)
            filter_input.remove()
        except NoMatches:
            pass  # already removed -- expected
        listview._filter_active = False
        self._is_filtered = False
        if restore:
            self.set_projects(list(self.app._projects))  # canonical list (D-09, Pitfall 3)
        def _restore_focus_and_cursor() -> None:
            listview.focus()
            if self._projects and listview.index is None:
                listview.index = 0  # restore blue bar lost after listview.clear()
        listview.call_after_refresh(_restore_focus_and_cursor)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """When highlight changes, notify parent with project data."""
        index = event.list_view.index  # ListView.Highlighted has no index attr in Textual 8.x
        if (
            event.item is not None
            and index is not None
            and index < len(self._projects)
        ):
            project = self._projects[index]
            # Validate label matches to guard against transient stale-index window
            # (set_projects replaces _projects synchronously but DOM mutations are async,
            # so a Highlighted event can fire with an index valid in the old list)
            label_widget = event.item.query_one(Label)
            if str(label_widget.renderable) == project.name:
                self.post_message(self.ProjectHighlighted(project))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """When Enter is pressed, post selection message (D-04)."""
        if (
            event.item is not None
            and event.index is not None
            and event.index < len(self._projects)
        ):
            self.post_message(self.ProjectSelected(self._projects[event.index]))
