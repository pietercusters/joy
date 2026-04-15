"""Tests for ProjectRow display."""
from __future__ import annotations

from joy.models import Project
from joy.widgets.project_list import ProjectRow


def _make_project(name: str = "my-project") -> Project:
    return Project(name=name)


def test_project_row_shows_project_name():
    """ProjectRow content includes the project name."""
    project = _make_project("test-project")
    row = ProjectRow(project)
    assert "test-project" in str(row.content)
