"""Project CRUD and persistence service. No I/O, no Textual imports."""
from __future__ import annotations

from datetime import datetime, timezone

from joy.models import ArchivedProject, ObjectItem, PresetKind, Project


class ProjectService:
    """Manages the project list: CRUD, validation, archival.

    Pure Python — zero Textual imports. Receives mutation requests and
    returns results. app.py handles persistence (@work decorators) and UI.
    """

    def __init__(self, projects: list[Project] | None = None) -> None:
        self._projects: list[Project] = projects or []

    @property
    def projects(self) -> list[Project]:
        """Read access to project list."""
        return self._projects

    def set_projects(self, projects: list[Project]) -> None:
        """Replace the internal project list (used after loading from disk)."""
        self._projects = projects

    def has_project(self, name: str) -> bool:
        """Check if a project with the given name exists."""
        return any(p.name == name for p in self._projects)

    def find_project(self, name: str) -> Project | None:
        """Return the first project matching name, or None."""
        for p in self._projects:
            if p.name == name:
                return p
        return None

    def create_project(
        self,
        name: str,
        repo: str | None = None,
        branch: str | None = None,
        default_open_kinds: list[str] | None = None,
    ) -> Project:
        """Create a new project and append to the list.

        Raises ValueError if a project with the same name already exists.
        """
        if self.has_project(name):
            raise ValueError(f"Project '{name}' already exists")
        project = Project(name=name, repo=repo)
        if branch:
            project.objects.append(
                ObjectItem(kind=PresetKind.BRANCH, value=branch)
            )
        self._projects.append(project)
        return project

    def add_object(
        self,
        project: Project,
        kind: PresetKind,
        value: str,
        default_open_kinds: list[str] | None = None,
    ) -> ObjectItem:
        """Create an ObjectItem and append to the project's objects."""
        obj = ObjectItem(
            kind=kind,
            value=value,
            open_by_default=kind.value in (default_open_kinds or []),
        )
        project.objects.append(obj)
        return obj

    def build_archived(self, project: Project) -> ArchivedProject:
        """Create an ArchivedProject snapshot with current UTC timestamp."""
        return ArchivedProject(
            project=project,
            archived_at=datetime.now(timezone.utc),
        )

    def remove_project(self, project: Project) -> bool:
        """Remove a project by identity. Returns True if removed."""
        try:
            self._projects.remove(project)
            return True
        except ValueError:
            return False
