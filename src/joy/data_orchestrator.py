"""Data loading coordination service. No I/O, no Textual imports."""
from __future__ import annotations

from joy.models import Config, ObjectItem, PresetKind, Project, Repo, TerminalSession, WorktreeInfo
from joy.resolver import RelationshipIndex, compute_relationships


class DataOrchestrator:
    """Coordinates background data loading, relationship computation, and propagation.

    Pure Python — zero Textual imports. Receives raw data from app.py's @work
    methods and returns computed results. app.py handles Textual lifecycle.
    """

    def __init__(self) -> None:
        self._worktrees_ready: bool = False
        self._sessions_ready: bool = False
        self._rel_index: RelationshipIndex | None = None
        self._current_worktrees: list[WorktreeInfo] = []
        self._current_sessions: list[TerminalSession] = []
        self._current_mr_data: dict = {}
        self._current_mr_authored: list = []

    # ---------------------------------------------------------------------------
    # Properties
    # ---------------------------------------------------------------------------

    @property
    def rel_index(self) -> RelationshipIndex | None:
        return self._rel_index

    @property
    def current_worktrees(self) -> list[WorktreeInfo]:
        return self._current_worktrees

    @property
    def current_sessions(self) -> list[TerminalSession]:
        return self._current_sessions

    @property
    def current_mr_data(self) -> dict:
        return self._current_mr_data

    @property
    def current_mr_authored(self) -> list:
        return self._current_mr_authored

    # ---------------------------------------------------------------------------
    # Data readiness
    # ---------------------------------------------------------------------------

    def mark_worktrees_ready(
        self,
        worktrees: list[WorktreeInfo],
        mr_data: dict | None = None,
        mr_authored: list | None = None,
    ) -> None:
        """Store worktree data and mark ready for relationship computation."""
        self._current_worktrees = worktrees
        self._current_mr_data = mr_data or {}
        self._current_mr_authored = mr_authored or []
        self._worktrees_ready = True

    def mark_sessions_ready(self, sessions: list[TerminalSession]) -> None:
        """Store session data and mark ready for relationship computation."""
        self._current_sessions = sessions
        self._sessions_ready = True

    # ---------------------------------------------------------------------------
    # Relationship computation
    # ---------------------------------------------------------------------------

    def maybe_compute_relationships(
        self,
        projects: list[Project],
        repos: list[Repo],
    ) -> RelationshipIndex | None:
        """Compute relationships when both worktrees and sessions are ready.

        Returns the new RelationshipIndex, or None if not both ready yet.
        Resets flags immediately to prevent stale-data races on next cycle.
        """
        if not (self._worktrees_ready and self._sessions_ready):
            return None
        self._worktrees_ready = False
        self._sessions_ready = False
        self._rel_index = compute_relationships(
            projects,
            self._current_worktrees,
            self._current_sessions,
            repos,
        )
        return self._rel_index

    # ---------------------------------------------------------------------------
    # MR auto-add propagation
    # ---------------------------------------------------------------------------

    def propagate_mr_auto_add(
        self,
        mr_data: dict,
        projects: list[Project],
        config: Config,
    ) -> list[str]:
        """Auto-add MR objects for detected PRs (PROP-02, D-02, D-03, D-05).

        Returns list of notification message strings. Mutates project.objects
        in place (appending new MR ObjectItem).
        """
        messages: list[str] = []
        if not mr_data:
            return messages
        for (repo_name, branch), mr_info in mr_data.items():
            if not mr_info.url:
                continue
            for project in projects:
                if project.repo is None:
                    continue
                if project.repo != repo_name:
                    continue
                has_branch = any(
                    obj.kind == PresetKind.BRANCH and obj.value == branch
                    for obj in project.objects
                )
                if not has_branch:
                    continue
                already_has_mr = any(
                    obj.kind == PresetKind.MR and obj.value == mr_info.url
                    for obj in project.objects
                )
                if already_has_mr:
                    continue
                new_mr = ObjectItem(
                    kind=PresetKind.MR,
                    value=mr_info.url,
                    label=f"PR #{mr_info.mr_number}",
                    open_by_default=PresetKind.MR.value in config.default_open_kinds,
                )
                project.objects.append(new_mr)
                messages.append(f"\u2295 Added PR #{mr_info.mr_number} to {project.name}")
        return messages

    # ---------------------------------------------------------------------------
    # Stale tab healing
    # ---------------------------------------------------------------------------

    def heal_stale_tabs(
        self,
        projects: list[Project],
        sessions: list[TerminalSession] | None,
        live_tab_ids: set[str],
    ) -> list[str]:
        """Clear orphaned iterm_tab_ids from projects.

        Returns list of project names that were healed.
        """
        if sessions is None:
            return []
        healed: list[str] = []
        for project in projects:
            if project.iterm_tab_id and project.iterm_tab_id not in live_tab_ids:
                project.iterm_tab_id = None
                healed.append(project.name)
        return healed

    # ---------------------------------------------------------------------------
    # Worktree link computation
    # ---------------------------------------------------------------------------

    def compute_linked_worktree_sets(
        self,
        projects: list[Project],
        worktrees: list[WorktreeInfo],
    ) -> tuple[set[str], set[tuple[str, str]]]:
        """Compute sets of linked worktree paths and branches.

        Returns (linked_paths, linked_branches) for fast CSS styling.
        """
        linked_paths: set[str] = set()
        linked_branches: set[tuple[str, str]] = set()
        for project in projects:
            for obj in project.objects:
                if obj.kind == PresetKind.WORKTREE:
                    if any(wt.path == obj.value for wt in worktrees):
                        linked_paths.add(obj.value)
                elif obj.kind == PresetKind.BRANCH and project.repo is not None:
                    if any(
                        wt.repo_name == project.repo and wt.branch == obj.value
                        for wt in worktrees
                    ):
                        linked_branches.add((project.repo, obj.value))
        return linked_paths, linked_branches

    # ---------------------------------------------------------------------------
    # Tab group computation
    # ---------------------------------------------------------------------------

    def build_tab_groups(
        self,
        projects: list[Project],
        live_tab_ids: set[str],
    ) -> list[tuple[str, str]]:
        """Build ordered tab groups for terminal pane display.

        Returns list of (project_name, tab_id) for projects with live tabs.
        """
        return [
            (p.name, p.iterm_tab_id)
            for p in projects
            if p.iterm_tab_id and p.iterm_tab_id in live_tab_ids
        ]
