"""Tests for WorktreePane cursor navigation and Enter activation.

Covers: BINDINGS presence, cursor init, j/k navigation, Enter -> MR URL,
Enter -> IDE open, and Enter noop when no rows.
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

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
    return MRInfo(
        mr_number=1,
        is_draft=False,
        ci_status=None,
        author="@dev",
        last_commit_hash="abc1234",
        last_commit_msg="feat: thing",
        url=url,
    )


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


def test_enter_opens_mr_url():
    """Enter on row with mr_info.url calls webbrowser.open with the URL."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    async def _run():
        app = _TestApp()
        with patch("joy.widgets.worktree_pane.webbrowser") as mock_wb:
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
                mock_wb.open.assert_called_once_with("https://github.com/x/y/pull/1")

    asyncio.run(_run())


def test_enter_opens_ide_when_no_mr():
    """Enter on row with mr_info=None calls subprocess.run with open -a."""
    from textual.app import App, ComposeResult

    from joy.models import Config

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    async def _run():
        app = _TestApp()
        app._config = Config(ide="PyCharm")
        with patch("joy.widgets.worktree_pane.subprocess") as mock_sp:
            async with app.run_test() as pilot:
                pane = app.query_one(WorktreePane)
                wt = _make_worktree("repo-a", "feat-1", "/tmp/wt1")
                await pane.set_worktrees([wt])
                await pilot.pause(0.1)
                pane.focus()
                await pilot.press("enter")
                await pilot.pause(0.1)
                mock_sp.run.assert_called_once()
                call_args = mock_sp.run.call_args[0][0]
                assert call_args[:3] == ["open", "-a", "PyCharm"], (
                    f"Expected open -a PyCharm, got: {call_args}"
                )
                assert "/tmp/wt1" in call_args, (
                    f"Expected worktree path in args, got: {call_args}"
                )

    asyncio.run(_run())


def test_enter_noop_when_no_rows():
    """With _cursor == -1 (no rows), Enter does not call webbrowser.open or subprocess.run."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    async def _run():
        app = _TestApp()
        with (
            patch("joy.widgets.worktree_pane.webbrowser") as mock_wb,
            patch("joy.widgets.worktree_pane.subprocess") as mock_sp,
        ):
            async with app.run_test() as pilot:
                pane = app.query_one(WorktreePane)
                # No set_worktrees call — _cursor remains -1
                assert pane._cursor == -1
                pane.focus()
                await pilot.press("enter")
                await pilot.pause(0.1)
                mock_wb.open.assert_not_called()
                mock_sp.run.assert_not_called()

    asyncio.run(_run())


@pytest.mark.slow
def test_cursor_identity_preserved_across_set_worktrees_rebuild():
    """After a DOM rebuild, cursor stays on same (repo_name, branch) identity (FOUND-03).

    Scenario:
      1. Load 3 worktrees; navigate to index 1 (feat-2)
      2. Call set_worktrees() again with same data in different order
      3. Cursor must still point to the row with branch=='feat-2', not index 1
    """
    from textual.app import App, ComposeResult

    from joy.models import WorktreeInfo
    from joy.widgets.worktree_pane import WorktreePane

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees_v1 = [
                WorktreeInfo("repo-a", "feat-1", "/tmp/wt1"),
                WorktreeInfo("repo-a", "feat-2", "/tmp/wt2"),
                WorktreeInfo("repo-a", "feat-3", "/tmp/wt3"),
            ]
            await pane.set_worktrees(worktrees_v1)
            await pilot.pause(0.1)
            # Navigate to feat-2 (index 1)
            pane.focus()
            await pilot.press("j")
            assert pane._cursor == 1
            assert pane._rows[1].branch == "feat-2"

            # Rebuild with same worktrees in different order (feat-3 first)
            worktrees_v2 = [
                WorktreeInfo("repo-a", "feat-3", "/tmp/wt3"),
                WorktreeInfo("repo-a", "feat-1", "/tmp/wt1"),
                WorktreeInfo("repo-a", "feat-2", "/tmp/wt2"),  # now at index 2
            ]
            await pane.set_worktrees(worktrees_v2)
            await pilot.pause(0.1)
            # Cursor must land on feat-2, which is now at index 2
            assert pane._rows[pane._cursor].branch == "feat-2", (
                f"Expected cursor on feat-2, got: {pane._rows[pane._cursor].branch!r} at index {pane._cursor}"
            )

    asyncio.run(_run())


@pytest.mark.slow
def test_cursor_clamps_when_item_gone_after_rebuild():
    """When highlighted worktree disappears, cursor clamps to min(saved_index, len-1) (D-14).

    Scenario:
      1. Load 3 worktrees; navigate to index 2 (last)
      2. Rebuild with only 1 worktree (last item removed)
      3. Cursor must be at index 0 (clamped, NOT -1)
    """
    from textual.app import App, ComposeResult

    from joy.models import WorktreeInfo
    from joy.widgets.worktree_pane import WorktreePane

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield WorktreePane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(WorktreePane)
            worktrees_v1 = [
                WorktreeInfo("repo-a", "feat-1", "/tmp/wt1"),
                WorktreeInfo("repo-a", "feat-2", "/tmp/wt2"),
                WorktreeInfo("repo-a", "feat-3", "/tmp/wt3"),
            ]
            await pane.set_worktrees(worktrees_v1)
            await pilot.pause(0.1)
            pane.focus()
            await pilot.press("j")
            await pilot.press("j")
            assert pane._cursor == 2  # at feat-3

            # Rebuild: feat-3 is gone, only feat-1 remains
            worktrees_v2 = [WorktreeInfo("repo-a", "feat-1", "/tmp/wt1")]
            await pane.set_worktrees(worktrees_v2)
            await pilot.pause(0.1)
            # Clamped to min(2, 0) = 0
            assert pane._cursor == 0, (
                f"Expected cursor clamped to 0, got {pane._cursor}"
            )

    asyncio.run(_run())
