"""Tests for cursor restoration across refresh/rebuild in ProjectList and ProjectDetail.

Covers the bug fix: both panes should preserve the user's cursor position (by identity)
when a rebuild/refresh cycle replaces the DOM children.
"""
from __future__ import annotations

import asyncio

from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.project_list import ProjectList


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(name: str, repo: str | None = None) -> Project:
    return Project(name=name, repo=repo)


def _make_projects(*names: str) -> list[Project]:
    return [_make_project(n) for n in names]


# ---------------------------------------------------------------------------
# ProjectList cursor restore tests
# ---------------------------------------------------------------------------


def test_project_list_preserves_cursor_on_same_list():
    """After set_projects with cursor on 'beta', re-calling set_projects
    with the same list preserves cursor on 'beta' (not reset to 0)."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield ProjectList(id="project-list")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            plist = app.query_one(ProjectList)
            projects = _make_projects("alpha", "beta", "gamma")
            plist.set_projects(projects)
            await pilot.pause(0.1)
            assert plist._cursor == 0
            # Move cursor to "beta" (index 1)
            plist.select_index(1)
            assert plist._cursor == 1
            assert plist._rows[1].project.name == "beta"
            # Re-call set_projects with the same list (simulates refresh)
            plist.set_projects(list(projects))
            await pilot.pause(0.1)
            # Cursor should still be on "beta"
            assert plist._cursor == 1, f"Expected cursor=1 (beta), got {plist._cursor}"
            assert plist._rows[plist._cursor].project.name == "beta"

    asyncio.run(_run())


def test_project_list_clamps_cursor_on_removal():
    """After set_projects with cursor on 'beta', re-calling set_projects
    with 'beta' removed clamps cursor to min(saved_index, len-1)."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield ProjectList(id="project-list")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            plist = app.query_one(ProjectList)
            projects = _make_projects("alpha", "beta", "gamma")
            plist.set_projects(projects)
            await pilot.pause(0.1)
            # Move cursor to "beta" (index 1)
            plist.select_index(1)
            assert plist._cursor == 1
            # Remove "beta" and re-set
            remaining = [p for p in projects if p.name != "beta"]
            plist.set_projects(remaining)
            await pilot.pause(0.1)
            # Cursor should clamp to min(1, len(remaining)-1) = min(1, 1) = 1
            assert plist._cursor == 1, f"Expected cursor=1 (clamped), got {plist._cursor}"

    asyncio.run(_run())


def test_project_list_first_call_starts_at_0():
    """First call to set_projects (cursor=-1, no prior selection) starts at index 0."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield ProjectList(id="project-list")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            plist = app.query_one(ProjectList)
            assert plist._cursor == -1
            projects = _make_projects("alpha", "beta")
            plist.set_projects(projects)
            await pilot.pause(0.1)
            assert plist._cursor == 0, f"Expected cursor=0 on first call, got {plist._cursor}"

    asyncio.run(_run())
