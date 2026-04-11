"""Textual pilot tests for the joy TUI."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from joy.app import JoyApp
from joy.models import ObjectItem, PresetKind, Project


def _sample_projects() -> list[Project]:
    """Create sample projects for testing.

    project-alpha: BRANCH "main" open_by_default=False, MR #1, WORKTREE "/tmp/alpha" open_by_default=True,
                   BRANCH "feature" open_by_default=True  (2 default objects total for ACT-02 tests)
    project-beta:  all open_by_default=False  (used for D-11 no-op test)
    project-empty: no objects
    """
    return [
        Project(
            name="project-alpha",
            objects=[
                ObjectItem(kind=PresetKind.BRANCH, value="main", open_by_default=False),
                ObjectItem(kind=PresetKind.MR, value="https://example.com/mr/1", label="MR #1"),
                ObjectItem(kind=PresetKind.WORKTREE, value="/tmp/alpha", open_by_default=True),
                ObjectItem(kind=PresetKind.BRANCH, value="feature", open_by_default=True),
            ],
        ),
        Project(
            name="project-beta",
            objects=[
                ObjectItem(kind=PresetKind.TICKET, value="https://notion.so/ticket-1", label="TICK-1", open_by_default=False),
            ],
        ),
        Project(
            name="project-empty",
            objects=[],
        ),
    ]


@pytest.fixture
def mock_store():
    """Mock store.load_projects and load_config to return sample data without touching ~/.joy/.

    Patched on joy.store (not joy.app) because app.py imports lazily:
    `from joy.store import load_projects` runs inside _load_data on each call,
    so the name is resolved from joy.store at call time — patch intercepts correctly.

    load_config is also patched so tests that depend on app._config use a known
    default Config() rather than whatever is in ~/.joy/config.toml on the host machine.
    """
    from joy.models import Config
    with patch("joy.store.load_projects", return_value=_sample_projects()), \
         patch("joy.store.load_config", return_value=Config()):
        yield


@pytest.fixture
def mock_operations():
    """Mock operations.open_object to avoid subprocess calls."""
    with patch("joy.operations.open_object") as mock:
        yield mock


@pytest.fixture
def mock_save():
    """Mock store.save_projects to avoid file I/O."""
    with patch("joy.store.save_projects") as mock:
        yield mock


@pytest.mark.asyncio
async def test_app_launches_with_two_panes(mock_store):
    """CORE-01: App shows two-pane layout."""
    app = JoyApp()
    async with app.run_test() as pilot:
        # Both panes should be present in the DOM
        assert app.query_one("#project-list") is not None
        assert app.query_one("#project-detail") is not None


@pytest.mark.asyncio
async def test_first_project_auto_selected(mock_store):
    """PROJ-02: First project is auto-selected on startup."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause()  # process all pending messages
        await app.workers.wait_for_complete()
        # The detail pane should show the first project's data
        detail = app.query_one("#project-detail")
        assert detail._project is not None
        assert detail._project.name == "project-alpha"


@pytest.mark.asyncio
async def test_enter_shifts_focus_to_detail(mock_store):
    """D-04: Enter on project shifts focus to detail pane."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)  # Let worker thread complete
        # Focus should start on the project list (ListView)
        await pilot.press("enter")
        await pilot.pause(0.1)
        # After Enter, focus should be on the detail pane
        focused = app.focused
        assert focused is not None
        assert focused.id == "project-detail"


@pytest.mark.asyncio
async def test_escape_returns_focus_to_list(mock_store):
    """D-06, CORE-04: Escape returns focus from detail to project list."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)  # Let worker thread complete
        # Move to detail pane
        await pilot.press("enter")
        await pilot.pause(0.1)
        # Press escape to go back
        await pilot.press("escape")
        await pilot.pause(0.1)
        # Focus should be back on the list
        focused = app.focused
        assert focused is not None
        # Should be the listview inside project-list
        assert focused.id in ("project-listview", "project-list")


@pytest.mark.asyncio
async def test_quit_with_q(mock_store):
    """App quits when q is pressed."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        # App should have exited (no assertion needed -- if it hangs, test fails by timeout)


# ---------------------------------------------------------------------------
# ACT-01: o key opens highlighted object
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_o_opens_object(mock_store, mock_operations):
    """ACT-01: Pressing o on a highlighted object calls open_object."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Press Enter to focus detail pane (project-alpha with BRANCH "main" highlighted)
        await pilot.press("enter")
        await pilot.pause(0.1)
        # Press o to open the highlighted object
        await pilot.press("o")
        await pilot.pause(0.1)
        await app.workers.wait_for_complete()
        assert mock_operations.called, "open_object should have been called"


@pytest.mark.asyncio
async def test_o_no_object_shows_error(mock_store):
    """ACT-01: Pressing o with no highlighted object shows error toast."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Navigate to project-empty (3rd project, index 2)
        await pilot.press("down")
        await pilot.press("down")
        await pilot.pause(0.1)
        # Press Enter to focus detail pane (empty project, no objects)
        await pilot.press("enter")
        await pilot.pause(0.1)
        detail = app.query_one("#project-detail")
        assert detail.highlighted_object is None, "Should have no highlighted object"
        # Press o — should show error toast without crashing
        await pilot.press("o")
        await pilot.pause(0.1)
        # App should still be running (no crash)
        assert app.is_running


@pytest.mark.asyncio
async def test_o_success_toast(mock_store, mock_operations):
    """ACT-01: Pressing o on highlighted object triggers success toast (no crash)."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("enter")
        await pilot.pause(0.1)
        # Mock open_object as no-op (already done by mock_operations fixture)
        await pilot.press("o")
        await pilot.pause(0.1)
        await app.workers.wait_for_complete()
        # open_object was called and app is still running
        assert mock_operations.called
        assert app.is_running


@pytest.mark.asyncio
async def test_o_failure_toast(mock_store):
    """ACT-01: Pressing o when open_object raises shows error toast."""
    import subprocess
    app = JoyApp()
    with patch("joy.operations.open_object", side_effect=subprocess.CalledProcessError(1, "open")):
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            await app.workers.wait_for_complete()
            await pilot.press("enter")
            await pilot.pause(0.1)
            await pilot.press("o")
            await pilot.pause(0.2)
            await app.workers.wait_for_complete()
            # App should still be running (exit_on_error=False prevents crash)
            assert app.is_running


# ---------------------------------------------------------------------------
# ACT-03: space key toggles open_by_default
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_space_toggles_default(mock_store, mock_save):
    """ACT-03: Pressing space flips open_by_default on the highlighted item."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Focus detail pane (project-alpha, first object is BRANCH "main" open_by_default=False)
        await pilot.press("enter")
        await pilot.pause(0.1)
        detail = app.query_one("#project-detail")
        item = detail.highlighted_object
        assert item is not None, "Should have a highlighted object"
        initial = item.open_by_default
        # Press space to toggle
        await pilot.press("space")
        await pilot.pause(0.1)
        assert item.open_by_default == (not initial), "open_by_default should have flipped"


@pytest.mark.asyncio
async def test_space_persists_toggle(mock_store, mock_save):
    """ACT-03: Pressing space calls save_projects to persist the toggle."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("enter")
        await pilot.pause(0.1)
        await pilot.press("space")
        await pilot.pause(0.1)
        await app.workers.wait_for_complete()
        assert mock_save.called, "save_projects should have been called to persist toggle"


# ---------------------------------------------------------------------------
# ACT-02: O key opens all open_by_default objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_O_opens_default_objects(mock_store, mock_operations, mock_save):
    """ACT-02: O opens all open_by_default objects for the current project."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("O")
        await pilot.pause(0.3)
        await app.workers.wait_for_complete()
        # project-alpha has 2 default objects: WORKTREE "/tmp/alpha" and BRANCH "feature"
        assert mock_operations.call_count == 2


@pytest.mark.asyncio
async def test_O_silent_noop_no_defaults(mock_store, mock_operations, mock_save):
    """ACT-02/D-11: O is a silent no-op when no default objects exist."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Navigate to project-beta (no defaults)
        await pilot.press("down")
        await pilot.pause(0.1)
        await pilot.press("O")
        await pilot.pause(0.3)
        await app.workers.wait_for_complete()
        assert mock_operations.call_count == 0


@pytest.mark.asyncio
async def test_O_works_from_project_list(mock_store, mock_operations, mock_save):
    """D-10: O fires from project list without pressing Enter (global binding)."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Do NOT press Enter -- stay on project list
        # Press O from project list
        await pilot.press("O")
        await pilot.pause(0.3)
        await app.workers.wait_for_complete()
        # project-alpha has 2 default objects
        assert mock_operations.call_count == 2
