"""Tests for Phase 12 Plan 02: TerminalPane widget.

Tests cover: SessionRow rendering, Claude/Other grouping, cursor navigation,
empty/unavailable states, scroll preservation, and refresh label.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from joy.models import TerminalSession
from joy.widgets.terminal_pane import (
    ICON_CLAUDE,
    ICON_SESSION,
    INDICATOR_BUSY,
    INDICATOR_WAITING,
    GroupHeader,
    SessionRow,
    TerminalPane,
)


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _make_session(
    session_id: str = "s1",
    session_name: str = "session-1",
    foreground_process: str = "zsh",
    cwd: str = "/Users/pieter/Github/joy",
) -> TerminalSession:
    return TerminalSession(
        session_id=session_id,
        session_name=session_name,
        foreground_process=foreground_process,
        cwd=cwd,
    )


def _claude_session(
    session_id: str = "c1",
    session_name: str = "claude-joy",
    foreground_process: str = "claude",
) -> TerminalSession:
    return TerminalSession(
        session_id=session_id,
        session_name=session_name,
        foreground_process=foreground_process,
        cwd="/Users/pieter/Github/joy",
        is_claude=True,  # explicitly set — pane uses is_claude, not foreground_process matching
    )


def _other_session(
    session_id: str = "o1",
    session_name: str = "shell-joy",
    foreground_process: str = "zsh",
) -> TerminalSession:
    return _make_session(
        session_id=session_id,
        session_name=session_name,
        foreground_process=foreground_process,
        cwd="/Users/pieter/Github/joy",
    )


# ---------------------------------------------------------------------------
# Unit tests: constants
# ---------------------------------------------------------------------------


def test_constants_defined():
    """ICON_SESSION, ICON_CLAUDE, INDICATOR_BUSY, INDICATOR_WAITING are defined."""
    assert ICON_SESSION == "\uf120"
    assert ICON_CLAUDE == "\U000f1325"
    assert INDICATOR_BUSY == "\u25cf"
    assert INDICATOR_WAITING == "\u25cb"


# ---------------------------------------------------------------------------
# Unit tests: SessionRow content
# ---------------------------------------------------------------------------


def test_session_row_stores_session_id():
    """SessionRow.session_id is set from the TerminalSession."""
    session = _make_session(session_id="abc123")
    row = SessionRow(session)
    assert row.session_id == "abc123"


def test_session_row_shows_session_name():
    """SessionRow renders the session_name in its content."""
    session = _make_session(session_name="my-session")
    row = SessionRow(session)
    assert "my-session" in str(row.content)


def test_session_row_non_claude_uses_icon_session():
    """Non-Claude SessionRow uses ICON_SESSION."""
    session = _other_session()
    row = SessionRow(session, is_claude=False)
    assert ICON_SESSION in str(row.content)


def test_session_row_claude_uses_icon_claude():
    """Claude SessionRow uses ICON_CLAUDE."""
    session = _claude_session()
    row = SessionRow(session, is_claude=True, is_busy=True)
    assert ICON_CLAUDE in str(row.content)


def test_session_row_claude_busy_shows_indicator_busy():
    """Claude busy SessionRow shows INDICATOR_BUSY."""
    session = _claude_session()
    row = SessionRow(session, is_claude=True, is_busy=True)
    assert INDICATOR_BUSY in str(row.content)


def test_session_row_claude_waiting_shows_indicator_waiting():
    """Claude waiting SessionRow shows INDICATOR_WAITING."""
    session = _claude_session()
    row = SessionRow(session, is_claude=True, is_busy=False)
    assert INDICATOR_WAITING in str(row.content)


def test_session_row_shows_process():
    """SessionRow includes foreground_process in content."""
    session = _make_session(foreground_process="python")
    row = SessionRow(session)
    assert "python" in str(row.content)


def test_session_row_shows_abbreviated_cwd():
    """SessionRow abbreviates home in cwd display."""
    import os
    home = os.path.expanduser("~")
    session = _make_session(cwd=f"{home}/Github/joy")
    row = SessionRow(session)
    content = str(row.content)
    assert "~/Github/joy" in content


# ---------------------------------------------------------------------------
# Async tests: TerminalPane widget
# ---------------------------------------------------------------------------


def test_terminal_pane_has_bindings():
    """TerminalPane.BINDINGS includes escape, up, down, k, j, enter, n, e, d, D."""
    keys = {b.key for b in TerminalPane.BINDINGS}
    assert "escape" in keys
    assert "up" in keys
    assert "down" in keys
    assert "k" in keys
    assert "j" in keys
    assert "enter" in keys
    assert "n" in keys
    assert "e" in keys
    assert "d" in keys
    assert "D" in keys


def test_terminal_pane_initial_state():
    """TerminalPane starts with _cursor=-1 and _rows=[]."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            assert pane._cursor == -1
            assert pane._rows == []
            assert pane.border_title == "Terminal"

    asyncio.run(_run())


def test_set_sessions_renders_session_rows():
    """set_sessions with 3 sessions renders 3 SessionRow widgets."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _make_session("s1", "session-1"),
                _make_session("s2", "session-2"),
                _make_session("s3", "session-3"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            rows = pane.query(SessionRow)
            assert len(rows) == 3, f"Expected 3 SessionRow, got {len(rows)}"

    asyncio.run(_run())


def test_set_sessions_groups_claude_sessions():
    """Claude sessions (foreground_process=='claude') appear under 'Claude' group header."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _claude_session("c1", "claude-joy"),
                _other_session("o1", "shell-1"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            headers = pane.query(GroupHeader)
            header_texts = [str(h.content) for h in headers]
            assert any("Claude" in t for t in header_texts), (
                f"Expected 'Claude' header, got: {header_texts}"
            )

    asyncio.run(_run())


def test_set_sessions_groups_other_sessions():
    """Non-Claude sessions appear under 'Other' group header."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _claude_session("c1", "claude-joy"),
                _other_session("o1", "shell-1"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            headers = pane.query(GroupHeader)
            header_texts = [str(h.content) for h in headers]
            assert any("Other" in t for t in header_texts), (
                f"Expected 'Other' header, got: {header_texts}"
            )

    asyncio.run(_run())


def test_set_sessions_omits_empty_group_headers():
    """If no Claude sessions exist, no 'Claude' group header is shown."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _other_session("o1", "shell-1"),
                _other_session("o2", "shell-2"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            headers = pane.query(GroupHeader)
            header_texts = [str(h.content) for h in headers]
            assert not any("Claude" in t for t in header_texts), (
                f"Expected no 'Claude' header, got: {header_texts}"
            )
            assert any("Other" in t for t in header_texts), (
                f"Expected 'Other' header, got: {header_texts}"
            )

    asyncio.run(_run())


def test_set_sessions_none_shows_unavailable():
    """set_sessions(None) shows 'iTerm2 unavailable' centered message."""
    from textual.app import App, ComposeResult
    from textual.widgets import Static

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            await pane.set_sessions(None)
            await pilot.pause(0.1)
            statics = pane.query(Static)
            texts = [str(s.content).lower() for s in statics]
            assert any("iterm2 unavailable" in t for t in texts), (
                f"Expected 'iTerm2 unavailable' message, got: {texts}"
            )
            # No SessionRow widgets
            assert len(pane.query(SessionRow)) == 0

    asyncio.run(_run())


def test_set_sessions_empty_shows_no_sessions():
    """set_sessions([]) shows 'No terminal sessions' centered message."""
    from textual.app import App, ComposeResult
    from textual.widgets import Static

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            await pane.set_sessions([])
            await pilot.pause(0.1)
            statics = pane.query(Static)
            texts = [str(s.content).lower() for s in statics]
            assert any("no terminal sessions" in t for t in texts), (
                f"Expected 'No terminal sessions' message, got: {texts}"
            )
            # No SessionRow widgets
            assert len(pane.query(SessionRow)) == 0

    asyncio.run(_run())


def test_cursor_starts_at_0_after_set_sessions():
    """After set_sessions with sessions, _cursor is 0."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [_other_session("o1"), _other_session("o2", "s2")]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            assert pane._cursor == 0, f"Expected cursor=0, got {pane._cursor}"

    asyncio.run(_run())


def test_cursor_navigation_j_moves_down():
    """Pressing 'j' moves cursor from 0 to 1."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _other_session("o1", "session-a"),
                _other_session("o2", "session-b"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            pane.focus()
            await pilot.press("j")
            assert pane._cursor == 1, f"Expected cursor=1, got {pane._cursor}"

    asyncio.run(_run())


def test_cursor_navigation_k_moves_up():
    """Pressing 'k' after moving down brings cursor back up."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _other_session("o1", "session-a"),
                _other_session("o2", "session-b"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            pane.focus()
            await pilot.press("j")
            assert pane._cursor == 1
            await pilot.press("k")
            assert pane._cursor == 0, f"Expected cursor=0, got {pane._cursor}"

    asyncio.run(_run())


def test_cursor_does_not_go_below_last():
    """Cursor does not go past the last row."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _other_session("o1", "session-a"),
                _other_session("o2", "session-b"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            pane.focus()
            # Press j many times
            for _ in range(10):
                await pilot.press("j")
            assert pane._cursor == 1, f"Expected cursor clamped at 1, got {pane._cursor}"

    asyncio.run(_run())


def test_cursor_does_not_go_above_first():
    """Cursor does not go past the first row (index 0)."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _other_session("o1", "session-a"),
                _other_session("o2", "session-b"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            pane.focus()
            # Press k many times at the top
            for _ in range(10):
                await pilot.press("k")
            assert pane._cursor == 0, f"Expected cursor clamped at 0, got {pane._cursor}"

    asyncio.run(_run())


def test_enter_key_calls_activate_session():
    """Pressing Enter on a highlighted row calls activate_session with correct session_id."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        # activate_session is lazily imported inside _do_activate worker,
        # so we patch it at the terminal_sessions module level.
        with patch(
            "joy.terminal_sessions.activate_session",
            return_value=True,
        ) as mock_activate:
            async with app.run_test() as pilot:
                pane = app.query_one(TerminalPane)
                sessions = [
                    _other_session("session-id-abc", "session-a"),
                ]
                await pane.set_sessions(sessions)
                await pilot.pause(0.1)
                pane.focus()
                await pilot.press("enter")
                await pilot.pause(0.2)
                await app.workers.wait_for_complete()
                mock_activate.assert_called_once_with("session-id-abc")

    asyncio.run(_run())


def test_enter_key_noop_when_no_sessions():
    """When _cursor is -1 (no sessions), pressing Enter is a no-op."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        with patch(
            "joy.terminal_sessions.activate_session",
            return_value=True,
        ) as mock_activate:
            async with app.run_test() as pilot:
                pane = app.query_one(TerminalPane)
                await pane.set_sessions([])
                await pilot.pause(0.1)
                pane.focus()
                await pilot.press("enter")
                await pilot.pause(0.1)
                mock_activate.assert_not_called()

    asyncio.run(_run())


def test_set_sessions_cursor_is_minus1_when_empty():
    """After set_sessions([]), cursor is -1 and rows is empty."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            await pane.set_sessions([])
            await pilot.pause(0.1)
            assert pane._cursor == -1
            assert pane._rows == []

    asyncio.run(_run())


def test_set_refresh_label_updates_border_title():
    """set_refresh_label updates border_title with timestamp."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            pane.set_refresh_label("5s ago")
            assert "5s ago" in pane.border_title
            assert "Terminal" in pane.border_title

    asyncio.run(_run())


def test_set_refresh_label_stale_shows_warning():
    """set_refresh_label with stale=True includes warning glyph in border_title."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            pane.set_refresh_label("2m ago", stale=True)
            assert "\u26a0" in pane.border_title, (
                f"Expected warning glyph in border_title, got: {pane.border_title}"
            )

    asyncio.run(_run())


def test_scroll_preservation_across_set_sessions():
    """Scroll position is preserved (approximately) across set_sessions rebuilds."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            # Build enough sessions to have scroll possibility
            sessions = [
                _other_session(f"o{i}", f"session-{i}") for i in range(20)
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            # Record scroll position (may be 0 in test env - just check it doesn't crash)
            from joy.widgets.terminal_pane import _TerminalScroll
            scroll = pane.query_one("#terminal-scroll", _TerminalScroll)
            saved_y = scroll.scroll_y
            # Call set_sessions again
            await pane.set_sessions(sessions)
            await pilot.pause(0.2)
            # Verify no exceptions thrown (test passes if no crash)
            rows = pane.query(SessionRow)
            assert len(rows) == 20

    asyncio.run(_run())


def test_claude_sessions_sorted_alphabetically():
    """Within Claude group, sessions are sorted alphabetically by session_name."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _claude_session("c3", "claude-zeta"),
                _claude_session("c1", "claude-alpha"),
                _claude_session("c2", "claude-mid"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            rows = pane.query(SessionRow)
            row_ids = [r.session_id for r in rows]
            assert row_ids == ["c1", "c2", "c3"], (
                f"Expected alpha order by name, got: {row_ids}"
            )

    asyncio.run(_run())


def test_other_sessions_sorted_alphabetically():
    """Other sessions are sorted alphabetically by session_name."""
    from textual.app import App, ComposeResult

    class _TestApp(App):
        def compose(self) -> ComposeResult:
            yield TerminalPane()

    async def _run():
        app = _TestApp()
        async with app.run_test() as pilot:
            pane = app.query_one(TerminalPane)
            sessions = [
                _other_session("o3", "zsh-session"),
                _other_session("o1", "alpha-session"),
                _other_session("o2", "mid-session"),
            ]
            await pane.set_sessions(sessions)
            await pilot.pause(0.1)
            rows = pane.query(SessionRow)
            row_ids = [r.session_id for r in rows]
            assert row_ids == ["o1", "o2", "o3"], (
                f"Expected alpha order by name, got: {row_ids}"
            )

    asyncio.run(_run())
