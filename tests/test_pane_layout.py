"""Tests for Phase 8: 4-pane grid layout and Tab focus cycling (PANE-01, PANE-02)."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from joy.app import JoyApp
from joy.models import Config, ObjectItem, PresetKind, Project


def _sample_projects() -> list[Project]:
    """Minimal project data for layout tests."""
    return [
        Project(
            name="project-alpha",
            objects=[
                ObjectItem(kind=PresetKind.BRANCH, value="main"),
                ObjectItem(kind=PresetKind.MR, value="https://example.com/mr/1"),
            ],
        ),
        Project(name="project-beta", objects=[]),
    ]


@pytest.fixture
def mock_store():
    """Mock store to avoid filesystem access."""
    with patch("joy.store.load_projects", return_value=_sample_projects()), \
         patch("joy.store.load_config", return_value=Config()):
        yield


# ---------------------------------------------------------------------------
# PANE-01: 4-pane grid layout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_four_panes_in_grid(mock_store):
    """PANE-01: App shows four panes -- projects (TL), detail (TR), terminal (BL), worktrees (BR)."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # All four panes must be queryable in the DOM
        assert app.query_one("#project-list") is not None
        assert app.query_one("#project-detail") is not None
        assert app.query_one("#terminal-pane") is not None
        assert app.query_one("#worktrees-pane") is not None


@pytest.mark.asyncio
async def test_grid_container_used(mock_store):
    """PANE-01/D-01: App uses a Grid container (not Horizontal)."""
    from textual.containers import Grid
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        grids = app.query(Grid)
        assert len(grids) >= 1, "App must contain at least one Grid container"


@pytest.mark.asyncio
async def test_stub_panes_show_coming_soon(mock_store):
    """PANE-01/D-09: Stub panes display centered 'coming soon' text."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        terminal = app.query_one("#terminal-pane")
        worktrees = app.query_one("#worktrees-pane")
        # Each should have a Static child with "coming soon"
        from textual.widgets import Static
        terminal_static = terminal.query_one(Static)
        worktrees_static = worktrees.query_one(Static)
        assert "coming soon" in str(terminal_static.content).lower()
        assert "coming soon" in str(worktrees_static.content).lower()


# ---------------------------------------------------------------------------
# PANE-02: Tab focus cycling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tab_cycles_four_panes(mock_store):
    """PANE-02/D-04: Tab visits all four panes in reading order TL->TR->BL->BR."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Initial focus should be on project list area
        focused = app.focused
        assert focused is not None

        # Collect pane IDs as we Tab through them
        pane_ids = []
        # Record starting pane
        pane_ids.append(_get_pane_id(app))

        for _ in range(3):
            await pilot.press("tab")
            await pilot.pause(0.05)
            pane_ids.append(_get_pane_id(app))

        # Should have visited 4 distinct panes
        assert len(set(pane_ids)) == 4, f"Expected 4 distinct panes, got: {pane_ids}"
        # Order must be: projects -> detail -> terminal -> worktrees
        expected_order = ["project-list", "project-detail", "terminal-pane", "worktrees-pane"]
        assert pane_ids == expected_order, f"Expected {expected_order}, got {pane_ids}"


@pytest.mark.asyncio
async def test_tab_wraps_around(mock_store):
    """PANE-02/D-05: Tab from last pane wraps to first pane."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Tab 4 times to cycle through all panes and wrap back
        for _ in range(4):
            await pilot.press("tab")
            await pilot.pause(0.05)
        # Should be back at the first pane (projects)
        pane_id = _get_pane_id(app)
        assert pane_id == "project-list", f"Expected wrap to project-list, got {pane_id}"


@pytest.mark.asyncio
async def test_shift_tab_reverses(mock_store):
    """PANE-02/D-04: Shift+Tab from projects pane goes to worktrees pane (reverse order)."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Focus should start on project list
        await pilot.press("shift+tab")
        await pilot.pause(0.05)
        pane_id = _get_pane_id(app)
        assert pane_id == "worktrees-pane", f"Expected worktrees-pane, got {pane_id}"


# ---------------------------------------------------------------------------
# D-13: sub_title updates per pane
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sub_title_updates_per_pane(mock_store):
    """D-13: sub_title shows the name of the focused pane."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()

        # Focus project list (initial)
        # sub_title starts as version but on_descendant_focus sets it on focus events
        # Force a focus event by tabbing away and back
        await pilot.press("tab")
        await pilot.pause(0.05)
        assert app.sub_title == "Detail"

        await pilot.press("tab")
        await pilot.pause(0.05)
        assert app.sub_title == "Terminal"

        await pilot.press("tab")
        await pilot.pause(0.05)
        assert app.sub_title == "Worktrees"

        await pilot.press("tab")
        await pilot.pause(0.05)
        assert app.sub_title == "Projects"


# ---------------------------------------------------------------------------
# Regression: existing v1.0 functionality still works
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_existing_project_list_navigation(mock_store):
    """Regression: j/k and arrow key navigation in project list works in Grid layout."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        detail = app.query_one("#project-detail")
        # Initial project should be project-alpha
        assert detail._project is not None
        assert detail._project.name == "project-alpha"
        # Navigate down to project-beta
        await pilot.press("down")
        await pilot.pause(0.1)
        assert detail._project.name == "project-beta"


@pytest.mark.asyncio
async def test_existing_enter_and_escape(mock_store):
    """Regression: Enter focuses detail, Escape returns to list in Grid layout."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Enter to focus detail
        await pilot.press("enter")
        await pilot.pause(0.1)
        focused = app.focused
        assert focused is not None
        assert focused.id == "project-detail"
        # Escape to return to list
        await pilot.press("escape")
        await pilot.pause(0.1)
        focused = app.focused
        assert focused is not None
        assert focused.id in ("project-listview", "project-list")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_pane_id(app: JoyApp) -> str:
    """Walk from focused widget up to find the pane container ID.

    Pane IDs: project-list, project-detail, terminal-pane, worktrees-pane.
    """
    pane_ids = {"project-list", "project-detail", "terminal-pane", "worktrees-pane"}
    node = app.focused
    while node is not None:
        if hasattr(node, "id") and node.id in pane_ids:
            return node.id
        node = node.parent
    # If focused widget itself is a pane
    if hasattr(app.focused, "id") and app.focused.id in pane_ids:
        return app.focused.id
    return f"unknown({app.focused})"
