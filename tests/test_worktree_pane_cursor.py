"""Tests for WorktreePane cursor navigation and Enter activation.

Covers: BINDINGS presence, cursor init, j/k navigation, Enter -> MR URL,
Enter -> IDE open, and Enter noop when no rows.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from joy.models import MRInfo, WorktreeInfo
from joy.widgets.worktree_pane import WorktreePane


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _make_worktree(
    repo_name: str = "repo-a",
    branch: str = "feat-x",
    path: str = "/tmp/wt",
) -> WorktreeInfo:
    return WorktreeInfo(repo_name=repo_name, branch=branch, path=path)


def _make_mr_info(url: str = "https://github.com/x/y/pull/1") -> MRInfo:
    return MRInfo(mr_number=1, is_draft=False, ci_status=None, url=url)


# ---------------------------------------------------------------------------
# Unit tests: pure (no Textual app)
# ---------------------------------------------------------------------------


def test_worktree_pane_has_bindings():
    """BINDINGS contains escape, up, down, k, j, enter — pure unit, no TUI."""
    keys = {b.key for b in WorktreePane.BINDINGS}
    assert "escape" in keys
    assert "up" in keys
    assert "down" in keys
    assert "k" in keys
    assert "j" in keys
    assert "enter" in keys


# ---------------------------------------------------------------------------
# Async Textual app tests (asyncio.run pattern, no @pytest.mark.asyncio)
# ---------------------------------------------------------------------------


def test_cursor_starts_at_0_after_set_worktrees():
    """_cursor == 0 after set_worktrees with 2 rows."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees = [
                _make_worktree("repo-a", "feat-1", "/tmp/wt1"),
                _make_worktree("repo-a", "feat-2", "/tmp/wt2"),
            ]
            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)
            assert pane._cursor == 0, f"Expected cursor=0 after set_worktrees, got {pane._cursor}"
            assert len(pane._rows) == 2, f"Expected 2 rows, got {len(pane._rows)}"

    asyncio.run(_run())


def test_cursor_navigation_j_moves_down():
    """press('j') changes _cursor from 0 to 1."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees = [
                _make_worktree("repo-a", "feat-1", "/tmp/wt1"),
                _make_worktree("repo-a", "feat-2", "/tmp/wt2"),
            ]
            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)
            pane.focus()
            await pilot.press("j")
            assert pane._cursor == 1, f"Expected cursor=1 after j, got {pane._cursor}"

    asyncio.run(_run())


def test_cursor_navigation_k_moves_up():
    """press('k') from _cursor=1 moves to 0."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees = [
                _make_worktree("repo-a", "feat-1", "/tmp/wt1"),
                _make_worktree("repo-a", "feat-2", "/tmp/wt2"),
            ]
            await pane.set_worktrees(worktrees)
            await pilot.pause(0.1)
            pane.focus()
            await pilot.press("j")
            assert pane._cursor == 1
            await pilot.press("k")
            assert pane._cursor == 0, f"Expected cursor=0 after k, got {pane._cursor}"

    asyncio.run(_run())


def test_enter_always_opens_ide_even_with_mr():
    """Enter on row with mr_info.url still delegates to action_open_ide (not webbrowser).

    After the mh6 refactor, Enter always opens IDE regardless of MR presence.
    The old 'Enter -> MR URL' path was removed in favour of a single code path.
    """
    from textual.app import App, ComposeResult

    ide_calls: list = []

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

        def action_open_ide(self) -> None:
            ide_calls.append("called")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            wt = _make_worktree("repo-a", "feat-1", "/tmp/wt1")
            mr = _make_mr_info(url="https://github.com/x/y/pull/1")
            mr_data = {("repo-a", "feat-1"): mr}
            await pane.set_worktrees([wt], mr_data=mr_data)
            await pilot.pause(0.1)
            pane.focus()
            await pilot.press("enter")
            await pilot.pause(0.1)
            assert ide_calls, "Expected action_open_ide to be called when Enter pressed on row with MR"

    asyncio.run(_run())


def test_enter_opens_ide_when_no_mr():
    """Enter on row with mr_info=None delegates to action_open_ide."""
    from textual.app import App, ComposeResult

    ide_calls: list = []

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

        def action_open_ide(self) -> None:
            ide_calls.append("called")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            wt = _make_worktree("repo-a", "feat-1", "/tmp/wt1")
            await pane.set_worktrees([wt])
            await pilot.pause(0.1)
            pane.focus()
            await pilot.press("enter")
            await pilot.pause(0.1)
            assert ide_calls, "Expected action_open_ide to be called when Enter pressed"

    asyncio.run(_run())


def test_enter_noop_when_no_rows():
    """With _cursor == -1 (no rows), Enter does not call action_open_ide."""
    from textual.app import App, ComposeResult

    ide_calls: list = []

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

        def action_open_ide(self) -> None:
            ide_calls.append("called")

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            # No set_worktrees call — _cursor remains -1
            assert pane._cursor == -1
            pane.focus()
            await pilot.press("enter")
            await pilot.pause(0.1)
            assert not ide_calls, "Expected no action_open_ide call when no rows"

    asyncio.run(_run())
