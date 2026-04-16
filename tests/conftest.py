"""Shared test fixtures for joy tests."""
from datetime import date

import pytest

from joy.models import Config, ObjectItem, PresetKind, Project


@pytest.fixture
def sample_config() -> Config:
    """Default config for testing."""
    return Config()


@pytest.fixture
def sample_object() -> ObjectItem:
    """A sample MR object item."""
    return ObjectItem(
        kind=PresetKind.MR,
        value="https://gitlab.com/project/repo/-/merge_requests/1",
        label="MR #1",
        open_by_default=True,
    )


@pytest.fixture
def sample_project(sample_object: ObjectItem) -> Project:
    """A project with several objects for testing."""
    return Project(
        name="test-project",
        objects=[
            sample_object,
            ObjectItem(kind=PresetKind.BRANCH, value="feature/test-branch", label="Branch"),
            ObjectItem(kind=PresetKind.TICKET, value="https://notion.so/ticket-123", label="Ticket"),
            ObjectItem(kind=PresetKind.THREAD, value="https://app.slack.com/thread/123", label="Thread"),
            ObjectItem(kind=PresetKind.FILE, value="/path/to/file.py", label="Main file"),
            ObjectItem(kind=PresetKind.NOTE, value="project-notes/daily.md", label="Notes"),
            ObjectItem(kind=PresetKind.WORKTREE, value="/Users/dev/worktrees/project", label="Worktree"),
            ObjectItem(kind=PresetKind.TERMINALS, value="test-project-agents", label="Terminals"),
            ObjectItem(kind=PresetKind.URL, value="https://docs.example.com", label="Docs"),
        ],
        created=date(2026, 1, 15),
    )
