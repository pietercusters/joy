"""Textual pilot tests for the joy TUI."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from joy.app import JoyApp
from joy.models import ObjectItem, PresetKind, Project


def _sample_projects() -> list[Project]:
    """Create sample projects for testing."""
    return [
        Project(
            name="project-alpha",
            objects=[
                ObjectItem(kind=PresetKind.BRANCH, value="main"),
                ObjectItem(kind=PresetKind.MR, value="https://example.com/mr/1", label="MR #1"),
                ObjectItem(kind=PresetKind.WORKTREE, value="/tmp/alpha"),
            ],
        ),
        Project(
            name="project-beta",
            objects=[
                ObjectItem(kind=PresetKind.TICKET, value="https://notion.so/ticket-1", label="TICK-1"),
            ],
        ),
    ]


@pytest.fixture
def mock_store():
    """Mock store.load_projects to return sample data without touching ~/.joy/.

    Patched on joy.store (not joy.app) because app.py imports lazily:
    `from joy.store import load_projects` runs inside _load_data on each call,
    so the name is resolved from joy.store at call time — patch intercepts correctly.
    """
    with patch("joy.store.load_projects", return_value=_sample_projects()) as mock:
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
