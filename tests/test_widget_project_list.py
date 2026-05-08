"""Tests for Phase 20: ProjectList widget with FakeBackend injection (TEST-04).

All tests use @pytest.mark.asyncio + pilot pattern. No @patch, no asyncio.run().
Data injected via set_projects() with canned Project lists.
"""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.project_list import GroupHeader, ProjectList, ProjectRow


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _sample_projects() -> list[Project]:
    return [
        Project(
            name="alpha",
            objects=[
                ObjectItem(kind=PresetKind.BRANCH, value="main"),
            ],
        ),
        Project(
            name="beta",
            objects=[
                ObjectItem(
                    kind=PresetKind.TICKET,
                    value="https://notion.so/123",
                    label="TICK-1",
                ),
            ],
        ),
        Project(name="gamma", objects=[]),
    ]


# ---------------------------------------------------------------------------
# Minimal test app
# ---------------------------------------------------------------------------


class _ProjectListTestApp(App):
    """Minimal app for testing ProjectList in isolation."""

    def compose(self) -> ComposeResult:
        yield ProjectList(id="project-list")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_project_list_renders_rows():
    """set_projects with 3 projects renders 3 ProjectRow widgets."""
    app = _ProjectListTestApp()
    async with app.run_test() as pilot:
        plist = app.query_one(ProjectList)
        plist.set_projects(_sample_projects(), [])
        await pilot.pause(0.3)
        rows = app.query(ProjectRow)
        assert len(rows) == 3, f"Expected 3 ProjectRow, got {len(rows)}"


@pytest.mark.asyncio
async def test_project_list_cursor_down():
    """Pressing 'j' moves cursor from 0 to 1."""
    app = _ProjectListTestApp()
    async with app.run_test() as pilot:
        plist = app.query_one(ProjectList)
        plist.set_projects(_sample_projects(), [])
        await pilot.pause(0.3)
        assert plist._cursor == 0, "Cursor should start at 0 after first set_projects"
        plist.focus()
        await pilot.press("j")
        assert plist._cursor == 1, f"Expected cursor 1 after j, got {plist._cursor}"


@pytest.mark.asyncio
async def test_project_list_current_project():
    """current_project returns the first project when cursor is at 0."""
    app = _ProjectListTestApp()
    async with app.run_test() as pilot:
        plist = app.query_one(ProjectList)
        plist.set_projects(_sample_projects(), [])
        await pilot.pause(0.3)
        assert plist.current_project is not None
        assert plist.current_project.name == "alpha"


@pytest.mark.asyncio
async def test_project_list_renders_group_headers():
    """set_projects renders GroupHeader widgets for status groups."""
    app = _ProjectListTestApp()
    async with app.run_test() as pilot:
        plist = app.query_one(ProjectList)
        # All three projects have status="idle" by default -> one group header
        plist.set_projects(_sample_projects(), [])
        await pilot.pause(0.3)
        headers = app.query(GroupHeader)
        assert len(headers) >= 1, f"Expected at least 1 GroupHeader, got {len(headers)}"
