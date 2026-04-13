"""Tests for Phase 10: WorktreePane scroll preservation and border_title refresh API.

Wave 1 (RED phase): These tests define the contract that Task 2 must satisfy.
- test_set_refresh_label_initial: should pass immediately (border_title defaults to "Worktrees")
- test_set_refresh_label_normal: FAILS until set_refresh_label is implemented
- test_set_refresh_label_stale: FAILS until set_refresh_label is implemented
- test_scroll_preserved_across_set_worktrees: FAILS until scroll preservation is implemented
- test_scroll_preserved_when_no_scroll: FAILS until scroll preservation is implemented
"""
from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult

from joy.models import WorktreeInfo
from joy.widgets.worktree_pane import WorktreePane


# ---------------------------------------------------------------------------
# Sample data helpers (self-contained — do not import from other test files)
# ---------------------------------------------------------------------------


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
            pane.set_worktrees(worktrees)
            await pilot.pause(0.1)

            # Scroll down
            scroll = pane.query_one("#worktree-scroll")
            scroll.scroll_to(y=50, animate=False)
            await pilot.pause(0.05)

            # Record position
            saved_y = scroll.scroll_y

            # Second call to rebuild
            pane.set_worktrees(worktrees)
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

            pane.set_worktrees(worktrees)
            await pilot.pause(0.1)

            scroll = pane.query_one("#worktree-scroll")
            assert scroll.scroll_y == 0, (
                f"Expected scroll_y=0 after first set_worktrees, got: {scroll.scroll_y}"
            )

            pane.set_worktrees(worktrees)
            await pilot.pause(0.1)

            assert scroll.scroll_y == 0, (
                f"Expected scroll_y=0 after second set_worktrees, got: {scroll.scroll_y}"
            )

    asyncio.run(_run())
