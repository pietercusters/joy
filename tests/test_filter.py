"""Integration tests for project list filter mode (PROJ-06)."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from joy.app import JoyApp
from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.project_list import ProjectList, ProjectRow

pytestmark = pytest.mark.slow


def _sample_projects() -> list[Project]:
    return [
        Project(name="project-alpha", objects=[
            ObjectItem(kind=PresetKind.BRANCH, value="main"),
        ]),
        Project(name="project-beta", objects=[
            ObjectItem(kind=PresetKind.TICKET, value="https://notion.so/t1", label="T1"),
        ]),
        Project(name="project-empty", objects=[]),
    ]


@pytest.fixture
def mock_store():
    from joy.models import Config
    with patch("joy.store.load_projects", return_value=_sample_projects()), \
         patch("joy.store.load_config", return_value=Config()):
        yield


@pytest.mark.asyncio
async def test_slash_mounts_filter_input(mock_store):
    """Test 1: Press /, verify Input#filter-input exists in DOM."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Press / to activate filter mode
        await pilot.press("/")
        await pilot.pause(0.1)
        # filter-input should now be mounted
        filter_input = app.query_one("#filter-input")
        assert filter_input is not None


@pytest.mark.asyncio
async def test_filter_realtime(mock_store):
    """Test 2: Press /, type 'alpha', verify only 1 item in list."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("/")
        await pilot.pause(0.1)
        # Type "alpha" into filter input
        for ch in "alpha":
            await pilot.press(ch)
        await pilot.pause(0.15)
        project_list = app.query_one("#project-list", ProjectList)
        assert len(project_list._rows) == 1


@pytest.mark.asyncio
async def test_filter_escape_restores_full_list(mock_store):
    """Test 3: Press /, type 'alpha', press Escape, verify 3 projects restored and Input removed."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("/")
        await pilot.pause(0.1)
        for ch in "alpha":
            await pilot.press(ch)
        await pilot.pause(0.15)
        # Press Escape to exit filter mode
        await pilot.press("escape")
        await pilot.pause(0.15)
        # All 3 projects should be restored
        project_list = app.query_one("#project-list", ProjectList)
        assert len(project_list._rows) == 3
        # Input should be removed
        assert len(app.query("#filter-input")) == 0


@pytest.mark.asyncio
async def test_filter_enter_keeps_subset(mock_store):
    """Test 4: Press /, type 'alpha', press Enter, verify Input removed but 1 item remains."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("/")
        await pilot.pause(0.1)
        for ch in "alpha":
            await pilot.press(ch)
        await pilot.pause(0.15)
        # Press Enter to exit filter mode keeping subset
        await pilot.press("enter")
        await pilot.pause(0.15)
        # Input should be removed
        assert len(app.query("#filter-input")) == 0
        # Filtered subset (1 item) should remain
        project_list = app.query_one("#project-list", ProjectList)
        assert len(project_list._rows) == 1


@pytest.mark.asyncio
async def test_filter_clear_restores_list(mock_store):
    """Test 5: Press /, type 'alpha', backspace 5 times to clear, verify 3 projects shown."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("/")
        await pilot.pause(0.1)
        for ch in "alpha":
            await pilot.press(ch)
        await pilot.pause(0.15)
        # Verify filtered (1 item)
        project_list = app.query_one("#project-list", ProjectList)
        assert len(project_list._rows) == 1
        # Clear by pressing backspace 5 times
        for _ in range(5):
            await pilot.press("backspace")
        await pilot.pause(0.15)
        # All 3 projects should be shown again
        assert len(project_list._rows) == 3


@pytest.mark.asyncio
async def test_filter_double_slash_noop(mock_store):
    """Test 6: Press / twice, verify only 1 Input#filter-input in DOM (no duplicate)."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("/")
        await pilot.pause(0.1)
        await pilot.press("/")
        await pilot.pause(0.1)
        # Only 1 filter input should exist
        assert len(app.query("#filter-input")) == 1


@pytest.mark.asyncio
async def test_filter_case_insensitive(mock_store):
    """Test 7: Press /, type 'ALPHA' (uppercase), verify project-alpha matches."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        await pilot.press("/")
        await pilot.pause(0.1)
        # Type uppercase
        for ch in "ALPHA":
            await pilot.press(ch)
        await pilot.pause(0.15)
        project_list = app.query_one("#project-list", ProjectList)
        assert len(project_list._rows) == 1
