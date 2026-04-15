"""Left pane: project list widget with keyboard navigation and repo grouping."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Static

from joy.models import Project, Repo
from joy.widgets.worktree_pane import ICON_BRANCH
from joy.widgets.terminal_pane import ICON_CLAUDE


# ---------------------------------------------------------------------------
# _ProjectScroll: non-focusable scroll container (same pattern as worktree_pane)
# ---------------------------------------------------------------------------


class _ProjectScroll(VerticalScroll, can_focus=False):
    """Non-focusable scroll container for project rows.

    Prevents VerticalScroll from stealing focus from ProjectList
    (VerticalScroll is focusable by default).
    """


# ---------------------------------------------------------------------------
# GroupHeader: repo section header (duplicated to avoid cross-widget coupling)
# ---------------------------------------------------------------------------


class GroupHeader(Static):
    """Repo section header for project grouping."""

    DEFAULT_CSS = """
    GroupHeader {
        width: 1fr;
        height: 1;
        color: $text-muted;
        text-style: bold;
        padding: 0 1;
    }
    """


# ---------------------------------------------------------------------------
# ProjectRow: single-line row for one project
# ---------------------------------------------------------------------------


class ProjectRow(Static):
    """Single-line row displaying one project with badge counts (D-09, D-10, D-11)."""

    DEFAULT_CSS = """
    ProjectRow {
        width: 1fr;
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(self, project: Project, **kwargs) -> None:
        self.project = project
        self._wt_count: int = 0
        self._agent_count: int = 0
        super().__init__(self._build_content(), **kwargs)

    def _build_content(self) -> str:
        """Build display string with project name and badge counts (D-09, D-10).

        Both counts always shown, even when zero (D-10: consistent row width).
        """
        return f" {self.project.name}  {ICON_BRANCH} {self._wt_count}  {ICON_CLAUDE} {self._agent_count}"

    def set_counts(self, wt_count: int, agent_count: int) -> None:
        """Update badge counts and trigger content re-render (D-11).

        Uses Static.update() — no DOM rebuild needed.
        """
        self._wt_count = wt_count
        self._agent_count = agent_count
        self.update(self._build_content())


# ---------------------------------------------------------------------------
# ProjectList: main widget with cursor navigation and repo grouping
# ---------------------------------------------------------------------------


class ProjectList(Widget, can_focus=True):
    """Left pane: project list grouped by repo with cursor navigation.

    Replaces the old ListView-based approach with VerticalScroll + GroupHeader
    + cursor/_rows/--highlight pattern (same as ProjectDetail, TerminalPane,
    WorktreePane). Projects are grouped under repo headers; unmatched projects
    appear under 'Other' (shown last).
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "select_project", "Open"),
        Binding("n", "new_project", "New", show=True),
        Binding("e", "rename_project", "Rename", show=True),
        Binding("D", "delete_project", "Delete", show=True),
        Binding("delete", "delete_project", "Delete", show=False),
        Binding("/", "filter", "Filter", show=True),
        Binding("R", "assign_repo", "Assign Repo", show=True),
    ]

    DEFAULT_CSS = """
    ProjectList:focus-within ProjectRow.--highlight {
        background: $accent;
    }
    ProjectList:focus ProjectRow.--highlight {
        background: $accent;
    }
    ProjectRow.--highlight {
        background: $accent 30%;
    }
    """

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
        self._repos: list[Repo] = []
        self._cursor: int = -1
        self._rows: list[ProjectRow] = []
        self._filter_active: bool = False
        self._is_filtered: bool = False
        self._render_generation: int = 0
        self.border_title = "Projects"

    def compose(self) -> ComposeResult:
        yield _ProjectScroll(id="project-scroll")

    def set_projects(self, projects: list[Project], repos: list[Repo] | None = None) -> None:
        """Populate the grouped project list. Called from JoyApp._set_projects.

        Args:
            projects: List of projects to display.
            repos: Optional list of repos for grouping. Falls back to self._repos.
        """
        self._projects = projects
        if repos is not None:
            self._repos = repos
        self._render_generation += 1
        gen = self._render_generation
        self.call_after_refresh(lambda: self._rebuild(gen))

    def _rebuild(self, gen: int = 0) -> None:
        """Rebuild the grouped project view inside the scroll container."""
        if gen != self._render_generation:
            return  # superseded by a newer set_projects call
        scroll = self.query_one("#project-scroll", _ProjectScroll)
        if not scroll.is_attached:
            # Scroll container not yet mounted -- reschedule
            self.call_after_refresh(lambda: self._rebuild(gen))
            return
        scroll.remove_children()

        # Group projects by repo
        repo_names = {r.name for r in self._repos} if self._repos else set()
        grouped: dict[str, list[Project]] = {}
        other: list[Project] = []
        for p in self._projects:
            if p.repo and p.repo in repo_names:
                grouped.setdefault(p.repo, []).append(p)
            else:
                other.append(p)

        new_rows: list[ProjectRow] = []

        # Mount repo groups alphabetically (D-09)
        for repo_name in sorted(grouped, key=str.lower):
            scroll.mount(GroupHeader(repo_name))
            for p in grouped[repo_name]:
                row = ProjectRow(p)
                scroll.mount(row)
                new_rows.append(row)

        # Mount "Other" group last (D-09)
        if other:
            if grouped:  # only show "Other" header when there are also repo groups
                scroll.mount(GroupHeader("Other"))
            for p in other:
                row = ProjectRow(p)
                scroll.mount(row)
                new_rows.append(row)

        self._rows = new_rows
        self._cursor = 0 if new_rows else -1
        self._update_highlight()

    def _update_highlight(self) -> None:
        """Apply '--highlight' CSS class to the row at the current cursor position."""
        for row in self._rows:
            row.remove_class("--highlight")
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].add_class("--highlight")
            self._rows[self._cursor].scroll_visible()
            self.post_message(self.ProjectHighlighted(self._rows[self._cursor].project))

    def action_cursor_up(self) -> None:
        """Move cursor up one row."""
        if self._cursor > 0:
            self._cursor -= 1
            self._update_highlight()

    def action_cursor_down(self) -> None:
        """Move cursor down one row."""
        if self._cursor < len(self._rows) - 1:
            self._cursor += 1
            self._update_highlight()

    def action_select_project(self) -> None:
        """Fire ProjectSelected message for the highlighted project (D-04)."""
        if 0 <= self._cursor < len(self._rows):
            self.post_message(self.ProjectSelected(self._rows[self._cursor].project))

    def action_rename_project(self) -> None:
        """Rename the highlighted project via a modal pre-filled with the current name."""
        from joy.screens.name_input import NameInputModal  # noqa: PLC0415 -- lazy import

        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        project = self._rows[self._cursor].project

        def on_name(name: str | None) -> None:
            if name is None:
                return  # Escape
            if name == project.name:
                return  # no change
            # Check for duplicate name
            if any(p.name == name and p is not project for p in self.app._projects):
                self.app.notify(f"Project '{name}' already exists", severity="error", markup=False)
                return
            project.name = name
            self.app._save_projects_bg()
            self.set_projects(list(self.app._projects), self._repos)

            def _restore_cursor() -> None:
                for i, row in enumerate(self._rows):
                    if row.project is project:
                        self.select_index(i)
                        break

            self.call_after_refresh(_restore_cursor)
            self.app.notify(f"Renamed to: '{name}'", markup=False)
            # Re-render the detail pane
            from joy.widgets.project_detail import ProjectDetail  # noqa: PLC0415

            try:
                self.app.query_one("#project-detail", ProjectDetail).set_project(project)
            except Exception:
                pass  # detail pane not mounted yet

        self.app.push_screen(
            NameInputModal(title="Rename Project", initial_value=project.name),
            on_name,
        )

    def action_delete_project(self) -> None:
        """Delete the highlighted project after confirmation (PROJ-05, D-12, D-13)."""
        from joy.screens import ConfirmationModal  # noqa: PLC0415 -- lazy import avoids circular dep

        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        project = self._rows[self._cursor].project
        cursor_at = self._cursor

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            projects = self.app._projects
            try:
                projects.remove(project)
            except ValueError:
                return  # already removed
            self.app._save_projects_bg()
            self.set_projects(projects, self._repos)
            if projects:
                # Select adjacent: next if available, else previous (D-13).
                new_index = min(cursor_at, len(projects) - 1)

                def _restore_selection() -> None:
                    self.focus()
                    self.select_index(new_index)

                self.call_after_refresh(_restore_selection)
            else:
                # No projects left -- clear detail pane
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

    def action_assign_repo(self) -> None:
        """Assign (or clear) the highlighted project's repo field (FLOW-01)."""
        from joy.screens.repo_picker import RepoPickerModal  # noqa: PLC0415

        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        if not self._repos:
            self.app.notify("No repos registered. Add one via Settings (s).", markup=False)
            return
        project = self._rows[self._cursor].project

        def on_pick(result: object) -> None:
            if result is RepoPickerModal.CANCELLED:
                return  # Escape — no change
            # result is str (repo name) or None (unassign)
            project.repo = result  # type: ignore[assignment]
            self.app._save_projects_bg()
            label = result if result else "(none)"
            self.app.notify(f"Assigned repo: {label} → '{project.name}'", markup=False)
            # Re-render to reflect new grouping
            self.set_projects(list(self.app._projects), self._repos)

        self.app.push_screen(
            RepoPickerModal(self._repos, current_repo=project.repo),
            on_pick,
        )

    def action_new_project(self) -> None:
        """Delegate to JoyApp.action_new_project (n only fires from project list focus)."""
        self.app.action_new_project()

    def action_filter(self) -> None:
        """Enter filter mode: mount Input above the scroll container (D-06)."""
        if self._filter_active:
            return  # already in filter mode -- no-op (prevent duplicate mount)
        self._is_filtered = False  # clear any Enter-kept filter state
        scroll = self.query_one("#project-scroll", _ProjectScroll)
        filter_input = Input(placeholder="Filter projects...", id="filter-input")
        self.mount(filter_input, before=scroll)
        self._filter_active = True
        filter_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter project list in real-time as user types (D-07)."""
        query = event.value.lower()
        if query:
            filtered = [p for p in self.app._projects if query in p.name.lower()]
        else:
            filtered = list(self.app._projects)  # empty string = full list (D-08)
        self._projects = filtered
        self._render_generation += 1
        gen = self._render_generation
        self.call_after_refresh(lambda: self._rebuild(gen))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter in filter input: dismiss filter, keep current subset (D-08)."""
        self._exit_filter_mode(restore=False)
        self._is_filtered = True  # list is still filtered; Escape will restore

    def on_key(self, event) -> None:
        """Handle Escape to exit filter mode without conflicting with modals (Pitfall 1)."""
        if event.key == "escape" and (self._filter_active or self._is_filtered):
            event.stop()
            self._exit_filter_mode(restore=True)

    def _exit_filter_mode(self, *, restore: bool = True) -> None:
        """Remove filter Input and optionally restore full project list (D-08, D-09)."""
        try:
            filter_input = self.query_one("#filter-input", Input)
            filter_input.remove()
        except NoMatches:
            pass  # already removed -- expected
        self._filter_active = False
        self._is_filtered = False
        if restore:
            self.set_projects(list(self.app._projects), self._repos)  # canonical list (D-09)

        def _restore_focus_and_cursor() -> None:
            self.focus()
            if self._rows and self._cursor < 0:
                self._cursor = 0
                self._update_highlight()

        self.call_after_refresh(_restore_focus_and_cursor)

    def sync_to(self, project_name: str) -> None:
        """Move cursor to matching project_name row without posting ProjectHighlighted.

        Silent cursor mutation for cross-pane sync. Does NOT call .focus(). (D-09, D-10)
        If no row matches, _cursor is left unchanged. (D-08)

        IMPORTANT: Do NOT use select_index() here — it calls _update_highlight() which
        posts ProjectHighlighted, creating a sync loop even with the _is_syncing guard.
        """
        for i, row in enumerate(self._rows):
            if row.project.name == project_name:
                self._cursor = i
                for r in self._rows:
                    r.remove_class("--highlight")
                row.add_class("--highlight")
                row.scroll_visible()
                return
        # No match: leave _cursor unchanged (D-08)

    def select_first(self) -> None:
        """Auto-select the first project (PROJ-02)."""
        if self._rows:
            self._cursor = 0
            self._update_highlight()

    def select_index(self, index: int) -> None:
        """Select project at given index."""
        if 0 <= index < len(self._rows):
            self._cursor = index
            self._update_highlight()

    def update_badges(self, index: object) -> None:
        """Push badge counts from RelationshipIndex to all project rows (D-11, BADGE-03).

        Called by JoyApp._update_badges() after every completed refresh cycle.
        """
        from joy.resolver import RelationshipIndex  # noqa: PLC0415 — avoid circular at module level
        for row in self._rows:
            wt_count = len(index.worktrees_for(row.project))  # type: ignore[union-attr]
            agent_count = len(index.agents_for(row.project))  # type: ignore[union-attr]
            row.set_counts(wt_count, agent_count)
