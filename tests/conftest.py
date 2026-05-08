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


@pytest.fixture(autouse=True, scope="session")
def _isolated_store_paths(tmp_path_factory):
    """Patch all joy.store path constants to a session-scoped tmp directory.

    Prevents any test from accidentally reading/writing ~/.joy/.
    Per D-13, D-14: uses pytest.MonkeyPatch() for session-scoped patching.
    """
    tmp = tmp_path_factory.mktemp("joy_store")
    mp = pytest.MonkeyPatch()
    mp.setattr("joy.store.JOY_DIR", tmp)
    mp.setattr("joy.store.PROJECTS_PATH", tmp / "projects.toml")
    mp.setattr("joy.store.CONFIG_PATH", tmp / "config.toml")
    mp.setattr("joy.store.REPOS_PATH", tmp / "repos.toml")
    mp.setattr("joy.store.ARCHIVE_PATH", tmp / "archive.toml")
    yield
    mp.undo()


# ---------------------------------------------------------------------------
# FakeBackend fixtures (Phase 20, TEST-04)
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_storage(sample_project):
    """FakeStorage pre-loaded with sample_project fixture."""
    from tests.fakes import FakeStorage
    from joy.ports import StoragePort

    storage = FakeStorage(projects=[sample_project])
    assert isinstance(storage, StoragePort)  # runtime Protocol check
    return storage


@pytest.fixture
def fake_terminal():
    """FakeTerminal with no sessions (simulates iTerm2 unavailable)."""
    from tests.fakes import FakeTerminal
    from joy.ports import TerminalPort

    terminal = FakeTerminal()
    assert isinstance(terminal, TerminalPort)
    return terminal


@pytest.fixture
def fake_git_data():
    """FakeGitData returning empty worktrees by default."""
    from tests.fakes import FakeGitData
    from joy.ports import GitDataPort

    git_data = FakeGitData()
    assert isinstance(git_data, GitDataPort)
    return git_data


@pytest.fixture
def fake_opener():
    """FakeOpener that records open calls without subprocess."""
    from tests.fakes import FakeOpener
    from joy.ports import OpenerPort

    opener = FakeOpener()
    assert isinstance(opener, OpenerPort)
    return opener
