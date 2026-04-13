"""Entry point for the joy CLI."""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.widgets import Footer, Header

from joy.models import Config, ObjectItem, PresetKind, Project, WorktreeInfo
from joy.screens import NameInputModal, PresetPickerModal, SettingsModal, ValueInputModal
from joy.widgets.object_row import _success_message, _truncate
from joy.widgets.project_detail import GROUP_ORDER, ProjectDetail
from joy.widgets.project_list import JoyListView, ProjectList
from joy.widgets.terminal_pane import TerminalPane
from joy.widgets.worktree_pane import WorktreePane


class JoyApp(App):
    """Keyboard-driven TUI for managing coding project artifacts."""

    TITLE = "joy"
    SUB_TITLE = "Projects"

    CSS = """
    #pane-grid {
        grid-size: 2 2;
        grid-rows: 1fr 1fr;
        grid-columns: 1fr 1fr;
    }
    #project-list {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    #project-list:focus-within {
        border: solid $accent;
    }
    #project-detail {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    #project-detail:focus-within {
        border: solid $accent;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        Binding("shift+o,O", "open_all_defaults", "Open All", priority=True),
        Binding("n", "new_project", "New", priority=True),
        Binding("s", "settings", "Settings", priority=True),
        Binding("r", "refresh_worktrees", "Refresh", priority=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._config: Config = Config()
        self._projects: list[Project] = []
        self._last_refresh_at: datetime | None = None
        self._refresh_failed: bool = False
        self._refresh_timer: object | None = None
        self._label_timer: object | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(
            ProjectList(id="project-list"),
            ProjectDetail(id="project-detail"),
            TerminalPane(id="terminal-pane"),
            WorktreePane(id="worktrees-pane"),
            id="pane-grid",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = _get_version()
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
        # WR-03: Create/reset timer here so it uses the user's configured interval,
        # not the default that was in effect when on_mount ran.
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        self._refresh_timer = self.set_interval(
            self._config.refresh_interval, self._trigger_worktree_refresh
        )
        if self._label_timer is None:
            self._label_timer = self.set_interval(5, self._update_refresh_label)
        self.query_one(ProjectList).set_projects(projects)
        if projects:
            self.query_one(ProjectList).select_first()
        self._load_worktrees()

    @work(thread=True)
    def _load_worktrees(self) -> None:
        """Load worktree data in background thread and push to pane (D-01, D-07)."""
        from joy.store import load_repos  # noqa: PLC0415
        from joy.worktrees import discover_worktrees  # noqa: PLC0415

        try:
            repos = load_repos()
            worktrees = discover_worktrees(repos, self._config.branch_filter)
            repo_count = len(repos)
            branch_filter = ", ".join(self._config.branch_filter) if self._config.branch_filter else ""
            self.app.call_from_thread(self._set_worktrees, worktrees, repo_count, branch_filter)
            self.app.call_from_thread(self._mark_refresh_success)
        except Exception:
            self.app.call_from_thread(self._mark_refresh_failure)

    async def _set_worktrees(self, worktrees: list[WorktreeInfo], repo_count: int, branch_filter: str) -> None:
        """Push worktree data to the pane widget (D-01)."""
        await self.query_one(WorktreePane).set_worktrees(
            worktrees, repo_count=repo_count, branch_filter=branch_filter
        )

    def _trigger_worktree_refresh(self) -> None:
        """Timer callback: re-run worktree discovery (D-07)."""
        self._load_worktrees()

    def action_refresh_worktrees(self) -> None:
        """Manual refresh triggered by 'r' keybinding (D-05). No toast (D-06)."""
        self._load_worktrees()

    def _mark_refresh_success(self) -> None:
        """Record successful refresh and update timestamp display."""
        self._last_refresh_at = datetime.now(timezone.utc)
        self._refresh_failed = False
        self._update_refresh_label()

    def _mark_refresh_failure(self) -> None:
        """Record failed refresh and update timestamp display with stale warning (REFR-04)."""
        self._refresh_failed = True
        self._update_refresh_label()

    def _update_refresh_label(self) -> None:
        """Push formatted timestamp to WorktreePane border_title (D-01, D-03)."""
        if self._last_refresh_at is None:
            if self._refresh_failed:
                # WR-05: No successful refresh yet but one has failed — show stale
                self.query_one(WorktreePane).set_refresh_label("never", stale=True)
            return  # No successful refresh yet
        now = datetime.now(timezone.utc)
        age_seconds = int((now - self._last_refresh_at).total_seconds())
        timestamp = self._format_age(age_seconds)
        # D-04: stale if age > 2x interval OR refresh failed
        stale = self._refresh_failed or age_seconds > (2 * self._config.refresh_interval)
        self.query_one(WorktreePane).set_refresh_label(timestamp, stale=stale)

    @staticmethod
    def _format_age(seconds: int) -> str:
        """Format age in seconds to human-readable relative string (D-02)."""
        if seconds < 5:
            return "just now"
        if seconds < 60:
            return f"{seconds}s ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        return f"{hours}h ago"

    def on_descendant_focus(self, event) -> None:
        """Update sub_title based on which pane has focus (D-08, D-13)."""
        node = event.widget
        while node is not None:
            if hasattr(node, "id"):
                if node.id == "project-detail":
                    self.sub_title = "Detail"
                    return
                if node.id in ("project-list", "project-listview"):
                    self.sub_title = "Projects"
                    return
                if node.id == "terminal-pane":
                    self.sub_title = "Terminal"
                    return
                if node.id == "worktrees-pane":
                    self.sub_title = "Worktrees"
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
        detail = self.query_one(ProjectDetail)
        detail.set_project(message.project)
        # Focus AFTER the DOM rebuild: set_project defers via call_after_refresh,
        # so focusing before that point lets the rebuild displace focus when
        # children are removed and re-mounted. Scheduling after ensures focus
        # lands on ProjectDetail once the DOM is stable.
        detail.call_after_refresh(detail.focus)

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

    def action_new_project(self) -> None:
        """Start project creation flow: name modal then add-object loop (D-01, D-02)."""
        def on_name(name: str | None) -> None:
            if name is None:
                return
            # D-04: Check duplicate name
            if any(p.name == name for p in self._projects):
                self.notify(f"Project '{name}' already exists", severity="error", markup=False)
                return
            # Create project, add to list, persist, refresh
            project = Project(name=name)
            self._projects.append(project)
            self._save_projects_bg()
            project_list = self.query_one(ProjectList)
            project_list.set_projects(self._projects)
            # Select the new project (last in list). Use call_after_refresh so
            # the reactive chain from set_projects (clear + append) settles
            # before we override the index — otherwise the ListView may reset
            # to index 0 after our select_index call.
            new_index = len(self._projects) - 1
            project_list.call_after_refresh(lambda: project_list.select_index(new_index))
            self.query_one(ProjectDetail).set_project(project)
            self.notify(f"Created project: '{name}'", markup=False)
            # D-02, D-03: Start add-object loop
            self._start_add_object_loop(project)
        self.push_screen(NameInputModal(), on_name)

    def _start_add_object_loop(self, project: Project) -> None:
        """Loop: preset picker -> value input -> repeat until Escape (D-03)."""
        def on_preset(preset: PresetKind | None) -> None:
            if preset is None:
                return  # Escape exits loop
            def on_value(value: str | None) -> None:
                if value is not None:
                    obj = ObjectItem(kind=preset, value=value)
                    project.objects.append(obj)
                    self._save_projects_bg()
                    self.query_one(ProjectDetail).set_project(project)
                    self.notify(f"Added: {preset.value} '{_truncate(value)}'", markup=False)
                # Loop: push preset picker again regardless of value result (D-03)
                self._start_add_object_loop(project)
            self.push_screen(ValueInputModal(preset), on_value)
        self.push_screen(PresetPickerModal(), on_preset)

    @work(thread=True, exit_on_error=False)
    def _save_projects_bg(self) -> None:
        """Persist projects to TOML in background thread (D-16)."""
        from joy.store import save_projects  # noqa: PLC0415
        save_projects(self._projects)

    def action_settings(self) -> None:
        """Open settings modal overlay (D-01, D-05, SETT-06)."""
        def on_settings(config: Config | None) -> None:
            if config is None:
                return  # Escaped -- no change (D-04)
            self._config = config
            self._save_config_bg()
            self.notify("Settings saved", markup=False)
        self.push_screen(SettingsModal(self._config), on_settings)

    @work(thread=True, exit_on_error=False)
    def _save_config_bg(self) -> None:
        """Persist config to TOML in background thread (D-04)."""
        from joy.store import save_config  # noqa: PLC0415
        save_config(self._config)

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
            except Exception as exc:
                display = _truncate(item.label if item.label else item.value)
                errors.append(f"{display}: {exc}")
        # Show accumulated error toasts at the end (D-07)
        for err in errors:
            self.app.notify(f"Failed to open: {err}", severity="error", markup=False)


def _get_version() -> str:
    """Return installed package version, or 'unknown' if not installed."""
    import importlib.metadata  # noqa: PLC0415
    try:
        return importlib.metadata.version("joy")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def main() -> None:
    """Main entry point for the joy CLI."""
    if "--version" in sys.argv:
        print(f"joy {_get_version()}")
        return
    app = JoyApp()
    app.run()


if __name__ == "__main__":
    main()
