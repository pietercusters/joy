"""Tests for Phase 20: WorktreePane widget with FakeBackend injection (TEST-04).

All tests use @pytest.mark.asyncio + pilot pattern. No @patch, no asyncio.run().
Data injected via set_worktrees() with canned WorktreeInfo lists.
"""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from joy.models import WorktreeInfo
from joy.widgets.worktree_pane import GroupHeader, WorktreePane, WorktreeRow


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _sample_worktrees() -> list[WorktreeInfo]:
    return [
        WorktreeInfo(
            repo_name="joy",
            branch="feat-z",
            path="/tmp/joy/wt/feat-z",
            is_dirty=True,
        ),
        WorktreeInfo(
            repo_name="joy",
            branch="feat-a",
            path="/tmp/joy/wt/feat-a",
            is_dirty=False,
        ),
        WorktreeInfo(
            repo_name="other",
            branch="develop",
            path="/tmp/other/wt/develop",
        ),
    ]


# ---------------------------------------------------------------------------
# Minimal test app
# ---------------------------------------------------------------------------


class _WorktreeTestApp(App):
    """Minimal app for testing WorktreePane in isolation."""

    def compose(self) -> ComposeResult:
        yield WorktreePane()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worktree_pane_renders_rows():
    """set_worktrees with 3 worktrees renders 3 WorktreeRow widgets."""
    app = _WorktreeTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(WorktreePane)
        await pane.set_worktrees(_sample_worktrees())
        await pilot.pause(0.1)
        rows = pane.query(WorktreeRow)
        assert len(rows) == 3, f"Expected 3 WorktreeRow, got {len(rows)}"


@pytest.mark.asyncio
async def test_worktree_pane_renders_group_headers():
    """set_worktrees with 2 repos renders 2 GroupHeader widgets."""
    app = _WorktreeTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(WorktreePane)
        await pane.set_worktrees(_sample_worktrees())
        await pilot.pause(0.1)
        headers = pane.query(GroupHeader)
        assert len(headers) == 2, f"Expected 2 GroupHeader (joy, other), got {len(headers)}"


@pytest.mark.asyncio
async def test_worktree_pane_cursor_down():
    """Pressing 'j' moves cursor from 0 to 1."""
    app = _WorktreeTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(WorktreePane)
        await pane.set_worktrees(_sample_worktrees())
        await pilot.pause(0.1)
        assert pane._cursor == 0, "Cursor should start at 0 after first set_worktrees"
        pane.focus()
        await pilot.press("j")
        assert pane._cursor == 1, f"Expected cursor 1 after j, got {pane._cursor}"
