"""Tests for cursor restoration across refresh/rebuild in ProjectList and ProjectDetail.

Covers the bug fix: both panes should preserve the user's cursor position (by identity)
when a rebuild/refresh cycle replaces the DOM children.
"""
from __future__ import annotations

import asyncio

from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.project_detail import ProjectDetail
from joy.widgets.project_list import ProjectList


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(name: str, repo: str | None = None, objects: list[ObjectItem] | None = None) -> Project:
    return Project(name=name, repo=repo, objects=objects or [])


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


# ---------------------------------------------------------------------------
# ProjectDetail cursor restore tests
# ---------------------------------------------------------------------------


def _make_detail_project() -> Project:
    """Create a project with 3 objects across different kinds for cursor tests."""
    return _make_project(
        "test-proj",
        objects=[
            ObjectItem(kind=PresetKind.BRANCH, value="main", label="main branch"),
            ObjectItem(kind=PresetKind.TICKET, value="https://ticket/1", label="TICK-1"),
            ObjectItem(kind=PresetKind.NOTE, value="https://note/1", label="My note"),
        ],
    )


def test_project_detail_preserves_cursor_on_refresh():
    """After set_project with cursor on TICKET, re-calling set_project
    preserves cursor on same TICKET (not reset to 0)."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield ProjectDetail(id="project-detail")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            detail = app.query_one(ProjectDetail)
            project = _make_detail_project()
            detail.set_project(project)
            await pilot.pause(0.1)
            # Find the TICKET row index
            ticket_idx = None
            for i, row in enumerate(detail._rows):
                if row.item.kind == PresetKind.TICKET:
                    ticket_idx = i
                    break
            assert ticket_idx is not None, "TICKET row not found"
            # Move cursor to TICKET
            detail._cursor = ticket_idx
            detail._update_highlight()
            # Re-call set_project (simulates refresh)
            detail.set_project(project)
            await pilot.pause(0.1)
            # Cursor should still be on the TICKET
            assert detail._rows[detail._cursor].item.kind == PresetKind.TICKET, (
                f"Expected cursor on TICKET, got {detail._rows[detail._cursor].item.kind}"
            )

    asyncio.run(_run())


def test_project_detail_clamps_cursor_on_removal():
    """After set_project with cursor on an object that gets removed,
    cursor clamps to min(saved_index, len-1)."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield ProjectDetail(id="project-detail")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            detail = app.query_one(ProjectDetail)
            project = _make_detail_project()
            detail.set_project(project)
            await pilot.pause(0.1)
            # Find the NOTE row and move cursor there (should be last)
            note_idx = None
            for i, row in enumerate(detail._rows):
                if row.item.kind == PresetKind.NOTE:
                    note_idx = i
                    break
            assert note_idx is not None, "NOTE row not found"
            detail._cursor = note_idx
            detail._update_highlight()
            saved_idx = detail._cursor
            # Remove the NOTE from objects
            project.objects = [o for o in project.objects if o.kind != PresetKind.NOTE]
            detail.set_project(project)
            await pilot.pause(0.1)
            # Cursor should clamp: min(saved_idx, len-1)
            expected = min(saved_idx, len(detail._rows) - 1)
            assert detail._cursor == expected, (
                f"Expected cursor={expected} (clamped), got {detail._cursor}"
            )

    asyncio.run(_run())


def test_project_detail_first_call_starts_at_0():
    """First call to set_project (cursor=-1) still starts at index 0."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield ProjectDetail(id="project-detail")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            detail = app.query_one(ProjectDetail)
            assert detail._cursor == -1
            project = _make_detail_project()
            detail.set_project(project)
            await pilot.pause(0.1)
            assert detail._cursor == 0, f"Expected cursor=0 on first call, got {detail._cursor}"

    asyncio.run(_run())


def test_project_detail_initial_cursor_takes_precedence():
    """When initial_cursor is explicitly passed (delete handler),
    it takes precedence over saved identity."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        _projects: list[Project] = []

        def compose(self) -> ComposeResult:
            yield ProjectDetail(id="project-detail")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            detail = app.query_one(ProjectDetail)
            project = _make_detail_project()
            detail.set_project(project)
            await pilot.pause(0.1)
            # Move cursor to last row
            last_idx = len(detail._rows) - 1
            detail._cursor = last_idx
            detail._update_highlight()
            # Use _set_project_with_cursor to force cursor=0
            detail._set_project_with_cursor(project, 0)
            await pilot.pause(0.1)
            assert detail._cursor == 0, (
                f"Expected cursor=0 (initial_cursor override), got {detail._cursor}"
            )
