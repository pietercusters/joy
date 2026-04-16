"""Pure-function cross-pane relationship resolver.

No I/O, no side effects. Computes relationships from lists of projects,
worktrees, and terminal sessions. Designed to be called after both
_set_worktrees and _set_terminal_sessions complete (D-07).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from joy.models import PresetKind, Project, Repo, TerminalSession, WorktreeInfo


@dataclass
class RelationshipIndex:
    """Bidirectional index of cross-pane relationships.

    Internal maps use project.name as key (stable string; avoids id() fragility).
    """

    # project.name -> list of matched worktrees / sessions
    _wt_for_project: dict[str, list[WorktreeInfo]] = field(default_factory=dict)
    _term_for_project: dict[str, list[TerminalSession]] = field(default_factory=dict)
    # inverse: worktree path -> project (path-based match)
    _project_for_wt_path: dict[str, Project] = field(default_factory=dict)
    # inverse: (repo_name, branch) -> project (branch-based match)
    _project_for_wt_branch: dict[tuple[str, str], Project] = field(default_factory=dict)
    # inverse: session_name -> project
    _project_for_terminal: dict[str, Project] = field(default_factory=dict)

    def worktrees_for(self, project: Project) -> list[WorktreeInfo]:
        """Return all worktrees matched to the given project."""
        return self._wt_for_project.get(project.name, [])

    def terminals_for(self, project: Project) -> list[TerminalSession]:
        """Return all terminal sessions matched to the given project."""
        return self._term_for_project.get(project.name, [])

    def project_for_worktree(self, wt: WorktreeInfo) -> Project | None:
        """Return the project that owns this worktree, or None.

        D-04: path match takes precedence over branch match.
        """
        return self._project_for_wt_path.get(wt.path) or \
               self._project_for_wt_branch.get((wt.repo_name, wt.branch))

    def project_for_terminal(self, session_name: str) -> Project | None:
        """Return the project that owns this terminal session, or None."""
        return self._project_for_terminal.get(session_name)


def compute_relationships(
    projects: list[Project],
    worktrees: list[WorktreeInfo],
    sessions: list[TerminalSession],
    repos: list[Repo],
) -> RelationshipIndex:
    """Compute cross-pane relationships from raw data lists (D-02).

    Two-pass approach: first build lookup maps from project objects,
    then scan worktrees/sessions to match them against those maps.
    O(n) build, O(1) lookup.

    Matching rules:
    - WORKTREE object value is an absolute path; matched against wt.path
    - BRANCH object value is a branch name; matched against (project.repo, branch)
    - D-04: path match takes precedence over branch match
    - D-05: projects with repo=None are excluded from branch-based matching
    - TERMINALS object value is a session name; matched against session.session_name
    """
    index = RelationshipIndex()

    # Pass 1: build lookup maps from project object lists (D-04, D-05)
    path_to_project: dict[str, Project] = {}                   # WORKTREE obj value -> project
    branch_to_project: dict[tuple[str, str], Project] = {}     # (repo, branch) -> project
    tab_id_to_project: dict[str, Project] = {}                 # tab_id -> project

    for project in projects:
        for obj in project.objects:
            if obj.kind == PresetKind.WORKTREE:
                path_to_project[obj.value] = project
            elif obj.kind == PresetKind.BRANCH and project.repo is not None:
                # D-05: exclude branch matching when project has no repo
                branch_to_project[(project.repo, obj.value)] = project
        # Tab-ID based terminal matching (replaces PresetKind.TERMINALS name matching)
        if project.iterm_tab_id:
            tab_id_to_project[project.iterm_tab_id] = project

    # Pass 2: match worktrees to projects
    for wt in worktrees:
        # D-04: path match takes precedence over branch match
        matched = path_to_project.get(wt.path)
        if matched is None:
            matched = branch_to_project.get((wt.repo_name, wt.branch))
        if matched is not None:
            index._wt_for_project.setdefault(matched.name, []).append(wt)
            # Populate inverse maps for project_for_worktree()
            if wt.path in path_to_project:
                index._project_for_wt_path[wt.path] = matched
            else:
                index._project_for_wt_branch[(wt.repo_name, wt.branch)] = matched

    # Pass 3: match sessions to projects by tab_id
    for session in sessions:
        matched = tab_id_to_project.get(session.tab_id) if session.tab_id else None
        if matched is not None:
            index._term_for_project.setdefault(matched.name, []).append(session)
            index._project_for_terminal[session.session_name] = matched

    return index
