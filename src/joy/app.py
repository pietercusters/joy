"""Entry point for the joy CLI."""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.widgets import Footer, Header

from joy.models import Config, ObjectItem, PresetKind, Project, Repo, TerminalSession, WorktreeInfo
from joy.resolver import RelationshipIndex
from joy.screens import NameInputModal, PresetPickerModal, SettingsModal, ValueInputModal
from joy.widgets.object_row import _success_message, _truncate
from joy.widgets.project_detail import SEMANTIC_GROUPS, ProjectDetail
from joy.widgets.project_list import ProjectList
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
        Binding("l", "legend", "Legend", priority=True),
        Binding("x", "toggle_sync", "Sync: on"),   # shown when sync is ON (D-11, D-13)
        Binding("x", "disable_sync", "Sync: off"),  # shown when sync is OFF
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._config: Config = Config()
        self._projects: list[Project] = []
        self._repos: list[Repo] = []
        self._last_refresh_at: datetime | None = None
        self._refresh_failed: bool = False
        self._mr_fetch_failed: bool = False
        self._refresh_timer: object | None = None
        self._label_timer: object | None = None
        self._terminal_last_refresh_at: datetime | None = None
        self._terminal_refresh_failed: bool = False
        # Phase 14: relationship resolver state (D-06, D-07)
        self._rel_index: RelationshipIndex | None = None
        self._worktrees_ready: bool = False
        self._sessions_ready: bool = False
        self._current_worktrees: list[WorktreeInfo] = []
        self._current_sessions: list[TerminalSession] = []
        # Phase 15: cross-pane sync guard (D-03)
        self._is_syncing: bool = False
        # Phase 15: sync toggle state (D-12, D-14) — toggle binding added in Plan 03
        self._sync_enabled: bool = True

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Control which sync toggle binding is visible in the footer. (D-13, SYNC-09)

        Returns True to show the binding, False to hide it from the footer entirely.
        At most one of toggle_sync / disable_sync is True at any time.
        """
        if action == "toggle_sync":
            return self._sync_enabled      # show "Sync: on" only when sync is enabled
        if action == "disable_sync":
            return not self._sync_enabled  # show "Sync: off" only when sync is disabled
        return super().check_action(action, parameters)

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
        """Load projects, config, and repos from store in a background thread (CP-1, CP-2)."""
        from joy.store import load_config, load_projects, load_repos  # noqa: PLC0415 — lazy import per CP-2

        projects = load_projects()
        config = load_config()
        repos = load_repos()
        self.app.call_from_thread(self._set_projects, projects, config, repos)

    def _set_projects(self, projects: list[Project], config: Config | None = None, repos: list[Repo] | None = None) -> None:
        """Update the project list widget with loaded projects (called from thread)."""
        self._projects = projects
        if config is not None:
            self._config = config
        if repos is not None:
            self._repos = repos
        # WR-03: Create/reset timer here so it uses the user's configured interval,
        # not the default that was in effect when on_mount ran.
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        self._refresh_timer = self.set_interval(
            self._config.refresh_interval, self._trigger_worktree_refresh
        )
        if self._label_timer is None:
            self._label_timer = self.set_interval(5, self._update_all_refresh_labels)
        self.query_one(ProjectList).set_projects(projects, self._repos)
        if projects:
            self.query_one(ProjectList).select_first()
        self._load_worktrees()
        self._load_terminal()

    @work(thread=True)
    def _load_worktrees(self) -> None:
        """Load worktree data in background thread and push to pane (D-01, D-07)."""
        from joy.store import load_repos  # noqa: PLC0415
        from joy.worktrees import discover_worktrees  # noqa: PLC0415
        from joy.mr_status import fetch_mr_data  # noqa: PLC0415

        try:
            repos = load_repos()
            worktrees = discover_worktrees(repos, self._config.branch_filter)

            # Phase 11 D-06: fetch MR/CI data in same thread
            mr_data: dict = {}
            mr_failed = False
            try:
                mr_data = fetch_mr_data(repos, worktrees)
                # No heuristic needed — fetch_mr_data returns {} for repos with no open MRs
            except Exception:
                mr_failed = True

            repo_count = len(repos)
            branch_filter = ", ".join(self._config.branch_filter) if self._config.branch_filter else ""
            self.app.call_from_thread(self._set_worktrees, worktrees, repo_count, branch_filter, mr_data, mr_failed)
            self.app.call_from_thread(self._mark_refresh_success)
        except Exception:
            self.app.call_from_thread(self._mark_refresh_failure)

    @work(thread=True, exit_on_error=False)
    def _load_terminal(self) -> None:
        """Load terminal session data in background thread (D-15). Independent of _load_worktrees."""
        from joy.terminal_sessions import fetch_sessions  # noqa: PLC0415

        try:
            sessions = fetch_sessions()
            self.app.call_from_thread(self._set_terminal_sessions, sessions)
            self.app.call_from_thread(self._mark_terminal_refresh_success)
        except Exception:
            self.app.call_from_thread(self._set_terminal_sessions, None)
            self.app.call_from_thread(self._mark_terminal_refresh_failure)

    async def _set_worktrees(
        self,
        worktrees: list[WorktreeInfo],
        repo_count: int,
        branch_filter: str,
        mr_data: dict | None = None,
        mr_failed: bool = False,
    ) -> None:
        """Push worktree data to the pane widget (D-01). Also captures data for resolver (D-07)."""
        self._mr_fetch_failed = mr_failed
        # Phase 14: store for resolver and set ready-flag (D-07, D-08)
        self._current_worktrees = worktrees
        self._worktrees_ready = True
        self._is_syncing = True  # suppress cross-pane sync during pane rebuild
        try:
            await self.query_one(WorktreePane).set_worktrees(
                worktrees, repo_count=repo_count, branch_filter=branch_filter, mr_data=mr_data
            )
        finally:
            self._is_syncing = False
        self._maybe_compute_relationships()

    async def _set_terminal_sessions(self, sessions: list[TerminalSession] | None) -> None:
        """Push terminal session data to the pane widget (D-15). Also captures data for resolver (D-07)."""
        # Phase 14: store for resolver (treat None as empty — pitfall 2 avoidance)
        self._current_sessions = sessions or []
        self._sessions_ready = True
        self._is_syncing = True  # suppress cross-pane sync during pane rebuild
        try:
            await self.query_one(TerminalPane).set_sessions(sessions)
        finally:
            self._is_syncing = False
        self._maybe_compute_relationships()

    def _maybe_compute_relationships(self) -> None:
        """Compute RelationshipIndex when both workers have completed their cycle (D-07, D-08).

        Called from _set_worktrees and _set_terminal_sessions — both run on the main thread
        via call_from_thread, so no asyncio coordination needed. Uses two boolean flags.
        Ready-flags are reset immediately to prevent stale-data races on subsequent cycles.
        """
        if not (self._worktrees_ready and self._sessions_ready):
            return
        # Reset flags before computing (prevents stale-data on next cycle)
        self._worktrees_ready = False
        self._sessions_ready = False
        from joy.resolver import compute_relationships  # noqa: PLC0415 — lazy import avoids import cycle
        self._rel_index = compute_relationships(
            self._projects,
            self._current_worktrees,
            self._current_sessions,
            self._repos,
        )
        self._update_badges()

    def _update_badges(self) -> None:
        """Push RelationshipIndex badge counts to ProjectList rows (D-08, D-11, BADGE-03)."""
        if self._rel_index is None:
            return
        try:
            self.query_one(ProjectList).update_badges(self._rel_index)
        except Exception:
            pass  # ProjectList not yet mounted — badges will be populated on next cycle

    def _trigger_worktree_refresh(self) -> None:
        """Timer callback: re-run worktree and terminal discovery (D-07, D-15)."""
        self._load_worktrees()
        self._load_terminal()

    def action_refresh_worktrees(self) -> None:
        """Manual refresh triggered by 'r' keybinding (D-05, D-15). No toast (D-06)."""
        self._load_worktrees()
        self._load_terminal()

    def _mark_refresh_success(self) -> None:
        """Record successful refresh and update timestamp display."""
        self._last_refresh_at = datetime.now(timezone.utc)
        self._refresh_failed = False
        self._update_refresh_label()

    def _mark_refresh_failure(self) -> None:
        """Record failed refresh and update timestamp display with stale warning (REFR-04)."""
        self._refresh_failed = True
        self._update_refresh_label()

    def _mark_terminal_refresh_success(self) -> None:
        """Record successful terminal refresh and update label."""
        self._terminal_last_refresh_at = datetime.now(timezone.utc)
        self._terminal_refresh_failed = False
        self._update_terminal_refresh_label()

    def _mark_terminal_refresh_failure(self) -> None:
        """Record failed terminal refresh and update label with stale warning."""
        self._terminal_refresh_failed = True
        self._update_terminal_refresh_label()

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
        self.query_one(WorktreePane).set_refresh_label(
            timestamp, stale=stale, mr_error=self._mr_fetch_failed
        )

    def _update_terminal_refresh_label(self) -> None:
        """Push formatted timestamp to TerminalPane border_title (D-16)."""
        if self._terminal_last_refresh_at is None:
            if self._terminal_refresh_failed:
                self.query_one(TerminalPane).set_refresh_label("never", stale=True)
            return
        now = datetime.now(timezone.utc)
        age_seconds = int((now - self._terminal_last_refresh_at).total_seconds())
        timestamp = self._format_age(age_seconds)
        stale = self._terminal_refresh_failed or age_seconds > (2 * self._config.refresh_interval)
        self.query_one(TerminalPane).set_refresh_label(timestamp, stale=stale)

    def _update_all_refresh_labels(self) -> None:
        """Periodic label update for both worktree and terminal panes."""
        self._update_refresh_label()
        self._update_terminal_refresh_label()

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
                if node.id in ("project-list", "project-scroll"):
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
        """When highlight moves, update detail pane and drive cross-pane sync. (SYNC-01, SYNC-02)"""
        if self._is_syncing:
            return
        self.query_one(ProjectDetail).set_project(message.project)
        if self._sync_enabled and self._rel_index is not None:
            self._sync_from_project(message.project)

    def _sync_from_project(self, project: Project) -> None:
        """Drive WorktreePane and TerminalPane to first items related to project. (D-04)

        Called with _is_syncing guard. Uses try/finally to always clear the guard.
        """
        self._is_syncing = True
        try:
            assert self._rel_index is not None
            worktrees = self._rel_index.worktrees_for(project)
            if worktrees:
                wt = worktrees[0]
                self.query_one(WorktreePane).sync_to(wt.repo_name, wt.branch)
            agents = self._rel_index.agents_for(project)
            if agents:
                self.query_one(TerminalPane).sync_to(agents[0].session_name)
        finally:
            self._is_syncing = False

    def on_worktree_pane_worktree_highlighted(
        self, message: WorktreePane.WorktreeHighlighted
    ) -> None:
        """Worktree cursor moved: sync ProjectList and TerminalPane. (SYNC-03, SYNC-04)"""
        if self._is_syncing:
            return
        if self._sync_enabled and self._rel_index is not None:
            self._sync_from_worktree(message.worktree)

    def _sync_from_worktree(self, worktree: WorktreeInfo) -> None:
        """Drive ProjectList and TerminalPane based on a highlighted worktree. (D-05)"""
        self._is_syncing = True
        try:
            assert self._rel_index is not None
            project = self._rel_index.project_for_worktree(worktree)
            if project is not None:
                self.query_one(ProjectList).sync_to(project.name)
                self.query_one(ProjectDetail).set_project(project)
                agents = self._rel_index.agents_for(project)
                if agents:
                    self.query_one(TerminalPane).sync_to(agents[0].session_name)
        finally:
            self._is_syncing = False

    def on_terminal_pane_session_highlighted(
        self, message: TerminalPane.SessionHighlighted
    ) -> None:
        """Agent session cursor moved: sync ProjectList and WorktreePane. (SYNC-05, SYNC-06)"""
        if self._is_syncing:
            return
        if self._sync_enabled and self._rel_index is not None:
            self._sync_from_session(message.session_name)

    def _sync_from_session(self, session_name: str) -> None:
        """Drive ProjectList and WorktreePane based on a highlighted agent session. (D-06)"""
        self._is_syncing = True
        try:
            assert self._rel_index is not None
            project = self._rel_index.project_for_agent(session_name)
            if project is not None:
                self.query_one(ProjectList).sync_to(project.name)
                self.query_one(ProjectDetail).set_project(project)
                worktrees = self._rel_index.worktrees_for(project)
                if worktrees:
                    wt = worktrees[0]
                    self.query_one(WorktreePane).sync_to(wt.repo_name, wt.branch)
        finally:
            self._is_syncing = False

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
        # Collect defaults in semantic group display order (D-06)
        defaults: list[ObjectItem] = []
        for _label, kinds in SEMANTIC_GROUPS:
            for kind in kinds:
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
            project_list.set_projects(self._projects, self._repos)
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
                # Repos may have been added/removed even if config was not saved
                self._reload_repos()
                return
            self._config = config
            self._save_config_bg()
            # Reload repos (may have been added/removed in the modal)
            self._reload_repos()
            self.notify("Settings saved", markup=False)
        self.push_screen(SettingsModal(self._config, self._repos), on_settings)

    def action_legend(self) -> None:
        """Toggle icon legend popup — dismiss if already open, else show."""
        from joy.screens import LegendModal  # noqa: PLC0415
        # Check if a LegendModal is already on the screen stack
        for screen in self.screen_stack:
            if isinstance(screen, LegendModal):
                screen.dismiss(None)
                return
        self.push_screen(LegendModal())

    def action_toggle_sync(self) -> None:
        """Disable cross-pane sync (called when sync is currently ON, key x). (SYNC-08, D-11)"""
        self._sync_enabled = False
        self.refresh_bindings()  # triggers Footer recompose via bindings_updated_signal

    def action_disable_sync(self) -> None:
        """Re-enable cross-pane sync (called when sync is currently OFF, key x). (SYNC-08)"""
        self._sync_enabled = True
        self.refresh_bindings()

    @work(thread=True, exit_on_error=False)
    def _save_config_bg(self) -> None:
        """Persist config to TOML in background thread (D-04)."""
        from joy.store import save_config  # noqa: PLC0415
        save_config(self._config)

    @work(thread=True, exit_on_error=False)
    def _reload_repos(self) -> None:
        """Reload repos from disk and refresh project grouping + worktrees."""
        from joy.store import load_repos  # noqa: PLC0415
        repos = load_repos()
        self.app.call_from_thread(self._apply_repos, repos)

    def _apply_repos(self, repos: list[Repo]) -> None:
        """Apply reloaded repos to the app state and refresh dependent widgets."""
        self._repos = repos
        self.query_one(ProjectList).set_projects(self._projects, self._repos)
        self._load_worktrees()

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
