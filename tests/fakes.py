"""Fake backend adapter classes for Phase 20 widget and snapshot tests.

All fakes conform to Protocol contracts defined in joy.ports via structural
subtyping (duck typing). Do NOT import joy.ports in this file.
"""
from __future__ import annotations

from joy.models import (
    ArchivedProject,
    Config,
    ObjectItem,
    Project,
    Repo,
    TerminalSession,
    WorktreeInfo,
)


class FakeStorage:
    """Fake StoragePort: returns canned data, tracks save calls."""

    def __init__(
        self,
        projects: list[Project] | None = None,
        config: Config | None = None,
        repos: list[Repo] | None = None,
        archived: list[ArchivedProject] | None = None,
    ):
        self.projects = projects or []
        self.config = config or Config()
        self.repos = repos or []
        self.archived = archived or []
        self.saved_projects: list[list[Project]] = []

    def load_projects(self) -> list[Project]:
        return self.projects

    def save_projects(self, projects: list[Project]) -> None:
        self.saved_projects.append(list(projects))

    def load_config(self) -> Config:
        return self.config

    def save_config(self, config: Config) -> None:
        pass

    def load_repos(self) -> list[Repo]:
        return self.repos

    def save_repos(self, repos: list[Repo]) -> None:
        pass

    def load_archived_projects(self) -> list[ArchivedProject]:
        return self.archived

    def save_archived_projects(self, projects: list[ArchivedProject]) -> None:
        pass


class FakeGitData:
    """Fake GitDataPort: returns canned worktrees, no subprocess."""

    def __init__(self, worktrees: list[WorktreeInfo] | None = None):
        self._worktrees = worktrees or []

    def discover_worktrees(
        self, repos: list[Repo], branch_filter: list[str]
    ) -> list[WorktreeInfo]:
        return self._worktrees


class FakeTerminal:
    """Fake TerminalPort: no iTerm2 subprocess calls, tracks activations."""

    def __init__(
        self,
        sessions: list[TerminalSession] | None = None,
        live_tab_ids: set[str] | None = None,
    ):
        self._sessions = sessions or []
        self._live_tab_ids = live_tab_ids or set()
        self.activated: list[str] = []
        self.closed_sessions: list[str] = []

    def fetch_sessions(self) -> tuple[list[TerminalSession], set[str]] | None:
        return (self._sessions, self._live_tab_ids) if self._sessions else None

    def create_tab(self, name: str) -> str | None:
        return None

    def activate_session(self, session_id: str) -> bool:
        self.activated.append(session_id)
        return True

    def close_session(self, session_id: str, *, force: bool = False) -> bool:
        self.closed_sessions.append(session_id)
        return True

    def close_tab(self, tab_id: str, *, force: bool = False) -> bool:
        return True

    def create_session(self, name: str) -> str | None:
        return None

    def rename_session(self, session_id: str, new_name: str) -> bool:
        return True


class FakeOpener:
    """Fake OpenerPort: records open_object calls without subprocess."""

    def __init__(self):
        self.opened: list[tuple[ObjectItem, Config]] = []

    def open_object(self, *, item: ObjectItem, config: Config) -> None:
        self.opened.append((item, config))
