"""Tests for Phase 10: WorktreePane scroll preservation and border_title refresh API.

Wave 1 (RED phase): These tests define the contract that Task 2 must satisfy.
- test_set_refresh_label_initial: should pass immediately (border_title defaults to "Worktrees")
- test_set_refresh_label_normal: FAILS until set_refresh_label is implemented
- test_set_refresh_label_stale: FAILS until set_refresh_label is implemented
- test_scroll_preserved_across_set_worktrees: FAILS until scroll preservation is implemented
- test_scroll_preserved_when_no_scroll: FAILS until scroll preservation is implemented

Wave 2 (integration tests for timer, r binding, stale detection):
- test_r_binding_triggers_refresh: FAILS until app.py has r binding + timestamp push
- test_timer_set_on_mount: FAILS until app.py creates _refresh_timer in on_mount
- test_refresh_failure_shows_stale: FAILS until app.py has stale detection
- test_no_toast_on_manual_refresh: FAILS until app.py action_refresh_worktrees has no notify
- test_timestamp_updates_after_refresh: FAILS until app.py pushes timestamp after refresh
"""
from __future__ import annotations

import asyncio

import pytest
from unittest.mock import patch

from textual.app import App, ComposeResult

from joy.app import JoyApp
from joy.models import Config, ObjectItem, PresetKind, Project, Repo, WorktreeInfo
from joy.widgets.worktree_pane import WorktreePane


# ---------------------------------------------------------------------------
# Sample data helpers (self-contained — do not import from other test files)
# ---------------------------------------------------------------------------


def _sample_projects() -> list[Project]:
    """Minimal project data to satisfy JoyApp store mocks."""
    return [
        Project(
            name="project-alpha",
            objects=[ObjectItem(kind=PresetKind.BRANCH, value="main")],
        ),
    ]


def _sample_repos() -> list[Repo]:
    """Two repos for store mocks."""
    return [
        Repo(name="joy", local_path="/tmp/joy"),
        Repo(name="other", local_path="/tmp/other"),
    ]


def _sample_worktrees() -> list[WorktreeInfo]:
    """Four WorktreeInfo covering both repos, both dirty/clean, both upstream states."""
    return [
        WorktreeInfo(
            repo_name="joy",
            branch="feat-z",
            path="/Users/pieter/Github/joy/wt/feat-z",
            is_dirty=True,
            has_upstream=True,
        ),
        WorktreeInfo(
            repo_name="joy",
            branch="feat-a",
            path="/Users/pieter/Github/joy/wt/feat-a",
            is_dirty=False,
            has_upstream=False,
        ),
        WorktreeInfo(
            repo_name="other",
            branch="develop",
            path="/Users/pieter/Github/other/wt/develop",
            is_dirty=False,
            has_upstream=True,
        ),
        WorktreeInfo(
            repo_name="other",
            branch="hotfix",
            path="/tmp/other/wt/hotfix",
            is_dirty=True,
            has_upstream=False,
        ),
    ]


def _many_worktrees(n: int = 25) -> list[WorktreeInfo]:
    """Generate n WorktreeInfo items (enough to overflow a typical terminal height)."""
    return [
        WorktreeInfo(
            repo_name="repo-a",
            branch=f"feat-{i:03d}",
            path=f"/Users/pieter/Github/repo-a/wt/feat-{i:03d}",
            is_dirty=(i % 3 == 0),
            has_upstream=(i % 2 == 0),
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Shared minimal test app
# ---------------------------------------------------------------------------


class _TestApp(App):
    """Minimal app for WorktreePane isolation tests."""

    def compose(self) -> ComposeResult:
        yield WorktreePane()


# ---------------------------------------------------------------------------
# Test 1: Initial border_title (should pass immediately — no implementation needed)
# ---------------------------------------------------------------------------


def test_set_refresh_label_initial():
    """Before any set_refresh_label call, border_title should be exactly 'Worktrees'."""

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            assert pane.border_title == "Worktrees", (
                f"Expected 'Worktrees', got: {repr(pane.border_title)}"
            )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Test 2: set_refresh_label with stale=False
# ---------------------------------------------------------------------------


def test_set_refresh_label_normal():
    """set_refresh_label('2m ago', stale=False) sets border_title to 'Worktrees  2m ago'."""

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            pane.set_refresh_label("2m ago", stale=False)
            assert pane.border_title == "Worktrees  2m ago", (
                f"Expected 'Worktrees  2m ago', got: {repr(pane.border_title)}"
            )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Test 3: set_refresh_label with stale=True
# ---------------------------------------------------------------------------


def test_set_refresh_label_stale():
    """set_refresh_label('2m ago', stale=True) includes warning glyph and timestamp."""

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            pane.set_refresh_label("2m ago", stale=True)
            title = str(pane.border_title)
            assert "\u26a0" in title, (
                f"Expected warning glyph (U+26A0) in border_title, got: {repr(title)}"
            )
            assert "2m ago" in title, (
                f"Expected timestamp '2m ago' in border_title, got: {repr(title)}"
            )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Test 4: Scroll position preserved across set_worktrees rebuilds
# ---------------------------------------------------------------------------


def test_scroll_preserved_across_set_worktrees():
    """Scroll position (scroll_y) is preserved when set_worktrees is called a second time."""

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees = _many_worktrees(25)

            # First call to populate
            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)

            # Scroll down
            scroll = pane.query_one("#worktree-scroll")
            scroll.scroll_to(y=50, animate=False)
            await pilot.pause(0.05)

            # Record position
            saved_y = scroll.scroll_y

            # Second call to rebuild
            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)

            # Scroll position should be preserved
            assert scroll.scroll_y == saved_y, (
                f"Expected scroll_y={saved_y}, got scroll_y={scroll.scroll_y} after set_worktrees rebuild"
            )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Test 5: Scroll position stays at 0 when content doesn't overflow
# ---------------------------------------------------------------------------


def test_scroll_preserved_when_no_scroll():
    """When scroll_y is 0 (content fits), set_worktrees leaves scroll_y at 0."""

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            # Use only 2 worktrees — unlikely to overflow in test terminal
            worktrees = _sample_worktrees()[:2]

            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)

            scroll = pane.query_one("#worktree-scroll")
            assert scroll.scroll_y == 0, (
                f"Expected scroll_y=0 after first set_worktrees, got: {scroll.scroll_y}"
            )

            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)

            assert scroll.scroll_y == 0, (
                f"Expected scroll_y=0 after second set_worktrees, got: {scroll.scroll_y}"
            )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Wave 2: Integration tests for timer, r binding, and stale detection
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_store_for_refresh():
    """Mock store with repos and worktrees for refresh integration tests."""
    with (
        patch("joy.store.load_projects", return_value=_sample_projects()),
        patch("joy.store.load_config", return_value=Config()),
        patch("joy.store.load_repos", return_value=_sample_repos()),
        patch("joy.worktrees.discover_worktrees", return_value=_sample_worktrees()),
    ):
        yield


@pytest.mark.asyncio
async def test_r_binding_triggers_refresh(mock_store_for_refresh):
    """Pressing 'r' triggers a worktree refresh and updates border_title with timestamp."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        title_before = app.query_one(WorktreePane).border_title
        await pilot.press("r")
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        title_after = app.query_one(WorktreePane).border_title
        assert title_after != "Worktrees", (
            f"Expected border_title to include timestamp after 'r', got: {repr(title_after)}"
        )
        assert "Worktrees" in str(title_after), (
            f"Expected 'Worktrees' prefix to be preserved, got: {repr(title_after)}"
        )


@pytest.mark.asyncio
async def test_timer_set_on_mount(mock_store_for_refresh):
    """After on_mount, the app's _refresh_timer attribute is not None."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        assert hasattr(app, "_refresh_timer"), (
            "Expected app to have _refresh_timer attribute after mount"
        )
        assert app._refresh_timer is not None, (
            "Expected app._refresh_timer to be set (not None) after on_mount"
        )


@pytest.mark.asyncio
async def test_refresh_failure_shows_stale(mock_store_for_refresh):
    """When refresh fails, border_title shows the stale warning icon (U+26A0)."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        # Now make discover_worktrees fail
        with patch("joy.worktrees.discover_worktrees", side_effect=Exception("git error")):
            await pilot.press("r")
            await pilot.pause(0.3)
            await app.workers.wait_for_complete()
        title = app.query_one(WorktreePane).border_title
        assert "\u26a0" in str(title), (
            f"Expected stale warning icon (U+26A0) in border_title after failure, got: {repr(title)}"
        )


@pytest.mark.asyncio
async def test_no_toast_on_manual_refresh(mock_store_for_refresh):
    """Pressing 'r' does NOT call app.notify — timestamp update is the only feedback (D-06)."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        with patch.object(app, "notify") as mock_notify:
            await pilot.press("r")
            await pilot.pause(0.2)
            await app.workers.wait_for_complete()
            mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_timestamp_updates_after_refresh(mock_store_for_refresh):
    """border_title includes a timestamp after initial load and after a manual refresh."""
    app = JoyApp()
    async with app.run_test() as pilot:
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        title1 = app.query_one(WorktreePane).border_title
        assert title1 != "Worktrees", (
            f"Expected border_title to include timestamp after initial load, got: {repr(title1)}"
        )
        await pilot.press("r")
        await pilot.pause(0.2)
        await app.workers.wait_for_complete()
        title2 = app.query_one(WorktreePane).border_title
        assert title2 != "Worktrees", (
            f"Expected border_title to still include timestamp after refresh, got: {repr(title2)}"
        )
        assert "Worktrees" in str(title2), (
            f"Expected 'Worktrees' prefix in border_title, got: {repr(title2)}"
        )
