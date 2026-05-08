"""Tests for Phase 20: TerminalPane widget with FakeBackend injection (TEST-04).

All tests use @pytest.mark.asyncio + pilot pattern. No @patch, no asyncio.run().
Data injected via set_sessions() with canned TerminalSession lists.
"""
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from joy.models import TerminalSession
from joy.widgets.terminal_pane import GroupHeader, SessionRow, TerminalPane


# ---------------------------------------------------------------------------
# Sample data helpers
# ---------------------------------------------------------------------------


def _make_session(
    session_id: str = "s1",
    session_name: str = "session-1",
    foreground_process: str = "zsh",
    cwd: str = "/Users/test",
    tab_id: str = "",
    is_claude: bool = False,
) -> TerminalSession:
    return TerminalSession(
        session_id=session_id,
        session_name=session_name,
        foreground_process=foreground_process,
        cwd=cwd,
        tab_id=tab_id,
        is_claude=is_claude,
    )


def _sample_sessions() -> list[TerminalSession]:
    return [
        _make_session("s1", "dev-session", "zsh"),
        _make_session("s2", "test-runner", "python"),
        _make_session("c1", "claude-joy", "claude", is_claude=True),
    ]


# ---------------------------------------------------------------------------
# Minimal test app
# ---------------------------------------------------------------------------


class _TerminalTestApp(App):
    """Minimal app for testing TerminalPane in isolation."""

    def compose(self) -> ComposeResult:
        yield TerminalPane()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminal_pane_renders_sessions():
    """set_sessions with 3 sessions renders 3 SessionRow widgets."""
    app = _TerminalTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(TerminalPane)
        await pane.set_sessions(_sample_sessions())
        await pilot.pause(0.1)
        rows = pane.query(SessionRow)
        assert len(rows) == 3, f"Expected 3 SessionRow, got {len(rows)}"


@pytest.mark.asyncio
async def test_terminal_pane_renders_group_headers():
    """set_sessions with mixed sessions renders group headers."""
    app = _TerminalTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(TerminalPane)
        # Without tab_groups, all sessions go to "Other" group -> 1 header
        await pane.set_sessions(_sample_sessions())
        await pilot.pause(0.1)
        headers = pane.query(GroupHeader)
        assert len(headers) == 1, f"Expected 1 GroupHeader (Other), got {len(headers)}"


@pytest.mark.asyncio
async def test_terminal_pane_renders_group_headers_with_tab_groups():
    """set_sessions with tab_groups creates separate group headers."""
    app = _TerminalTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(TerminalPane)
        sessions = [
            _make_session("s1", "dev-session", "zsh", tab_id="tab-1"),
            _make_session("c1", "claude-joy", "claude", is_claude=True),
        ]
        tab_groups = [("my-project", "tab-1")]
        await pane.set_sessions(sessions, tab_groups=tab_groups)
        await pilot.pause(0.1)
        headers = pane.query(GroupHeader)
        # "my-project" group + "Other" group = 2 headers
        assert len(headers) == 2, f"Expected 2 GroupHeader, got {len(headers)}"


@pytest.mark.asyncio
async def test_terminal_pane_cursor_down():
    """Pressing 'j' moves cursor from 0 to 1."""
    app = _TerminalTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(TerminalPane)
        await pane.set_sessions(_sample_sessions())
        await pilot.pause(0.1)
        assert pane._cursor == 0, "Cursor should start at 0 after first set_sessions"
        pane.focus()
        await pilot.press("j")
        assert pane._cursor == 1, f"Expected cursor 1 after j, got {pane._cursor}"
