"""Protocol contracts for joy service boundaries. No I/O, no side effects."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from joy.models import (
    ArchivedProject,
    Config,
    ObjectItem,
    Project,
    Repo,
    TerminalSession,
    WorktreeInfo,
)


# ---------------------------------------------------------------------------
# StoragePort
# ---------------------------------------------------------------------------


@runtime_checkable
class StoragePort(Protocol):
    """Contract for project/config persistence."""

    def load_projects(self) -> list[Project]: ...

    def save_projects(self, projects: list[Project]) -> None: ...

    def load_config(self) -> Config: ...

    def save_config(self, config: Config) -> None: ...

    def load_repos(self) -> list[Repo]: ...

    def save_repos(self, repos: list[Repo]) -> None: ...

    def load_archived_projects(self) -> list[ArchivedProject]: ...

    def save_archived_projects(self, projects: list[ArchivedProject]) -> None: ...


# ---------------------------------------------------------------------------
# GitDataPort
# ---------------------------------------------------------------------------


@runtime_checkable
class GitDataPort(Protocol):
    """Contract for git data discovery."""

    def discover_worktrees(
        self, repos: list[Repo], branch_filter: list[str]
    ) -> list[WorktreeInfo]: ...


# ---------------------------------------------------------------------------
# TerminalPort
# ---------------------------------------------------------------------------


@runtime_checkable
class TerminalPort(Protocol):
    """Contract for terminal session management."""

    def fetch_sessions(self) -> tuple[list[TerminalSession], set[str]] | None: ...

    def create_tab(self, name: str) -> str | None: ...

    def activate_session(self, session_id: str) -> bool: ...

    def close_session(self, session_id: str, *, force: bool) -> bool: ...

    def close_tab(self, tab_id: str, *, force: bool) -> bool: ...

    def create_session(self, name: str) -> str | None: ...

    def rename_session(self, session_id: str, new_name: str) -> bool: ...


# ---------------------------------------------------------------------------
# OpenerPort
# ---------------------------------------------------------------------------


@runtime_checkable
class OpenerPort(Protocol):
    """Contract for opening objects (URLs, files, etc.)."""

    def open_object(self, *, item: ObjectItem, config: Config) -> None: ...


# ---------------------------------------------------------------------------
# SyncablePane
# ---------------------------------------------------------------------------


@runtime_checkable
class SyncablePane(Protocol):
    """Contract for panes that support cross-pane sync."""

    def sync_to(self, *args: str) -> bool: ...

    def clear_selection(self) -> None: ...
