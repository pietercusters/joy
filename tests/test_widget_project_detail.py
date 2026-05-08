"""Tests for Phase 20: ProjectDetail widget with FakeBackend injection (TEST-04).

All tests use @pytest.mark.asyncio + pilot pattern. No @patch, no asyncio.run().
Data injected via set_project() with canned Project.
"""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.object_row import ObjectRow
from joy.widgets.project_detail import ProjectDetail


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _sample_project() -> Project:
    return Project(
        name="test-proj",
        objects=[
            ObjectItem(kind=PresetKind.BRANCH, value="main", label="Main branch"),
            ObjectItem(
                kind=PresetKind.MR,
                value="https://gitlab.com/mr/1",
                label="MR #1",
            ),
            ObjectItem(
                kind=PresetKind.TICKET,
                value="https://notion.so/123",
                label="TICK-1",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Minimal test app
# ---------------------------------------------------------------------------


class _ProjectDetailTestApp(App):
    """Minimal app for testing ProjectDetail in isolation."""

    def compose(self) -> ComposeResult:
        yield ProjectDetail(id="project-detail")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_project_detail_renders_objects():
    """set_project renders ObjectRow for each stored object."""
    app = _ProjectDetailTestApp()
    async with app.run_test() as pilot:
        detail = app.query_one(ProjectDetail)
        detail.set_project(_sample_project())
        await pilot.pause(0.5)
        rows = app.query(ObjectRow)
        assert len(rows) == 3, f"Expected 3 ObjectRow, got {len(rows)}"


@pytest.mark.asyncio
async def test_project_detail_cursor_down():
    """Pressing 'j' moves cursor from 0 to 1."""
    app = _ProjectDetailTestApp()
    async with app.run_test() as pilot:
        detail = app.query_one(ProjectDetail)
        detail.set_project(_sample_project())
        await pilot.pause(0.5)
        assert detail._cursor == 0, "Cursor should start at 0"
        detail.focus()
        await pilot.press("j")
        assert detail._cursor == 1, f"Expected cursor 1 after j, got {detail._cursor}"


@pytest.mark.asyncio
async def test_project_detail_clear():
    """clear() removes all ObjectRow widgets and resets state."""
    app = _ProjectDetailTestApp()
    async with app.run_test() as pilot:
        detail = app.query_one(ProjectDetail)
        detail.set_project(_sample_project())
        await pilot.pause(0.5)
        assert detail.current_project is not None
        detail.clear()
        await pilot.pause(0.1)
        assert detail.current_project is None
        rows = app.query(ObjectRow)
        assert len(rows) == 0, f"Expected 0 ObjectRow after clear, got {len(rows)}"
