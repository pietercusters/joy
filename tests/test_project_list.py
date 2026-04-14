"""Tests for ProjectRow badge display (BADGE-01, BADGE-02)."""
from __future__ import annotations

import pytest
from joy.models import Project
from joy.widgets.project_list import ProjectRow
from joy.widgets.worktree_pane import ICON_BRANCH
from joy.widgets.terminal_pane import ICON_CLAUDE


def _make_project(name: str = "my-project") -> Project:
    return Project(name=name)


def test_project_row_shows_project_name():
    """ProjectRow content includes the project name."""
    project = _make_project("test-project")
    row = ProjectRow(project)
    assert "test-project" in str(row.content)


def test_project_row_shows_badge_icons_initially_zero():
    """ProjectRow shows both badge icons even when counts are zero (D-10)."""
    project = _make_project()
    row = ProjectRow(project)
    content = str(row.content)
    assert ICON_BRANCH in content, f"Expected ICON_BRANCH in content, got: {content!r}"
    assert ICON_CLAUDE in content, f"Expected ICON_CLAUDE in content, got: {content!r}"
    assert "0" in content, f"Expected '0' counts in content, got: {content!r}"


def test_project_row_set_counts_updates_worktree_count():
    """set_counts(wt_count=3, agent_count=0) reflects wt_count in content (BADGE-01)."""
    project = _make_project()
    row = ProjectRow(project)
    row.set_counts(wt_count=3, agent_count=0)
    content = str(row.content)
    assert "3" in content, f"Expected '3' in content after set_counts, got: {content!r}"
    assert ICON_BRANCH in content


def test_project_row_set_counts_updates_agent_count():
    """set_counts(wt_count=0, agent_count=2) reflects agent_count in content (BADGE-02)."""
    project = _make_project()
    row = ProjectRow(project)
    row.set_counts(wt_count=0, agent_count=2)
    content = str(row.content)
    assert "2" in content, f"Expected '2' in content after set_counts, got: {content!r}"
    assert ICON_CLAUDE in content


def test_project_row_set_counts_both():
    """set_counts(wt_count=5, agent_count=3) shows both counts (D-10)."""
    project = _make_project()
    row = ProjectRow(project)
    row.set_counts(wt_count=5, agent_count=3)
    content = str(row.content)
    assert "5" in content and "3" in content, f"Expected both counts in content, got: {content!r}"


def test_project_row_set_counts_updates_content_without_error():
    """set_counts() can be called multiple times without error."""
    project = _make_project()
    row = ProjectRow(project)
    row.set_counts(1, 0)
    row.set_counts(0, 2)
    row.set_counts(5, 5)
    content = str(row.content)
    assert "5" in content
