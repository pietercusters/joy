"""Cross-pane sync coordination service. No I/O, no Textual imports."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from joy.models import Project, TerminalSession, WorktreeInfo
from joy.resolver import RelationshipIndex


class PaneCoordinator:
    """Coordinates cross-pane selection sync across all 6 directions.

    Pure Python — zero Textual imports. Operates on duck-typed pane objects
    that provide sync_to(*args) -> bool and clear_selection() -> None.

    The syncing context manager prevents infinite sync loops by setting a
    guard flag that event handlers check before triggering further syncs.
    """

    def __init__(self) -> None:
        self._is_syncing: bool = False

    @property
    def is_syncing(self) -> bool:
        """True while a sync operation is in progress."""
        return self._is_syncing

    @contextmanager
    def syncing(self):
        """Context manager that sets the sync guard flag."""
        self._is_syncing = True
        try:
            yield
        finally:
            self._is_syncing = False

    # ---------------------------------------------------------------------------
    # Sync direction 1-2: Project -> WorktreePane, TerminalPane
    # ---------------------------------------------------------------------------

    def sync_from_project(
        self,
        project: Project,
        rel_index: RelationshipIndex,
        wt_pane: Any,
        term_pane: Any,
    ) -> None:
        """Drive WorktreePane and TerminalPane to items related to project.

        Calls clear_selection() on panes that cannot match the active project.
        """
        with self.syncing():
            worktrees = rel_index.worktrees_for(project)
            if worktrees:
                wt = worktrees[0]
                matched = wt_pane.sync_to(wt.repo_name, wt.branch)
                if not matched:
                    wt_pane.clear_selection()
            else:
                wt_pane.clear_selection()

            terminals = rel_index.terminals_for(project)
            if terminals:
                matched = term_pane.sync_to(terminals[0].session_name)
                if not matched:
                    term_pane.clear_selection()
            else:
                term_pane.clear_selection()

    # ---------------------------------------------------------------------------
    # Sync direction 3-4: Worktree -> ProjectList, TerminalPane
    # ---------------------------------------------------------------------------

    def sync_from_worktree(
        self,
        worktree: WorktreeInfo,
        rel_index: RelationshipIndex,
        project_list: Any,
        detail_pane: Any,
        term_pane: Any,
    ) -> None:
        """Drive ProjectList and TerminalPane based on a highlighted worktree.

        Calls clear_selection() on TerminalPane when no terminal matches.
        """
        with self.syncing():
            project = rel_index.project_for_worktree(worktree)
            if project is not None:
                project_list.sync_to(project.name)
                resolver_wts = rel_index.worktrees_for(project)
                resolver_terms = rel_index.terminals_for(project)
                detail_pane.set_project(
                    project,
                    resolver_worktrees=resolver_wts,
                    resolver_terminals=resolver_terms,
                )
                if resolver_terms:
                    matched = term_pane.sync_to(resolver_terms[0].session_name)
                    if not matched:
                        term_pane.clear_selection()
                else:
                    term_pane.clear_selection()
            else:
                term_pane.clear_selection()

    # ---------------------------------------------------------------------------
    # Sync direction 5-6: Session -> ProjectList, WorktreePane
    # ---------------------------------------------------------------------------

    def sync_from_session(
        self,
        session_name: str,
        rel_index: RelationshipIndex,
        project_list: Any,
        detail_pane: Any,
        wt_pane: Any,
    ) -> None:
        """Drive ProjectList and WorktreePane based on a highlighted session.

        Calls clear_selection() on WorktreePane when no worktree matches.
        """
        with self.syncing():
            project = rel_index.project_for_terminal(session_name)
            if project is not None:
                project_list.sync_to(project.name)
                worktrees = rel_index.worktrees_for(project)
                terminals = rel_index.terminals_for(project)
                detail_pane.set_project(
                    project,
                    resolver_worktrees=worktrees,
                    resolver_terminals=terminals,
                )
                if worktrees:
                    wt = worktrees[0]
                    matched = wt_pane.sync_to(wt.repo_name, wt.branch)
                    if not matched:
                        wt_pane.clear_selection()
                else:
                    wt_pane.clear_selection()
            else:
                wt_pane.clear_selection()
