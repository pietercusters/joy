"""Unit tests for terminal_sessions module. All iTerm2 API calls are mocked."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from joy.terminal_sessions import _SHELL_PROCESSES, activate_session, fetch_sessions


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_mock_session(
    session_id: str = "w0t0p0:12345",
    name: str = "Session 1",
    job_name: str = "zsh",
    cwd: str = "/Users/test",
) -> MagicMock:
    """Return a mock iterm2 Session object."""
    session = MagicMock()
    session.session_id = session_id
    session.name = name

    async def _async_get_variable(var_name: str):
        if var_name == "jobName":
            return job_name
        if var_name == "path":
            return cwd
        return None

    session.async_get_variable = _async_get_variable
    session.async_activate = AsyncMock()
    return session


def _make_mock_app(sessions: list, session_by_id: dict | None = None) -> MagicMock:
    """Return a mock iterm2 App object with terminal_windows, tabs, sessions."""
    tab = MagicMock()
    tab.sessions = sessions

    window = MagicMock()
    window.tabs = [tab]

    app = MagicMock()
    app.terminal_windows = [window]

    if session_by_id is not None:
        app.get_session_by_id = lambda sid: session_by_id.get(sid)
    else:
        app.get_session_by_id = lambda sid: None

    app.async_activate = AsyncMock()
    return app


# ---------------------------------------------------------------------------
# fetch_sessions tests
# ---------------------------------------------------------------------------


class TestFetchSessions:
    def test_fetch_sessions_returns_list_when_api_reachable(self):
        """fetch_sessions() returns a list of TerminalSession when iTerm2 is reachable."""
        mock_session = _make_mock_session(
            session_id="w0t0p0:abc",
            name="Main",
            job_name="claude",
            cwd="/Users/test/project",
        )
        mock_app = _make_mock_app([mock_session])

        def run_until_complete(coro_fn, retry=False):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(coro_fn(_make_connection()))
            finally:
                loop.close()

        def _make_connection():
            return MagicMock()

        with (
            patch("iterm2.async_get_app", AsyncMock(return_value=mock_app)),
            patch(
                "iterm2.connection.Connection.run_until_complete",
                side_effect=run_until_complete,
            ),
        ):
            result = fetch_sessions()

        assert result is not None
        assert len(result) == 1
        ts = result[0]
        assert ts.session_id == "w0t0p0:abc"
        assert ts.session_name == "Main"
        assert ts.foreground_process == "claude"
        assert ts.cwd == "/Users/test/project"

    def test_fetch_sessions_returns_none_on_connection_refused(self):
        """fetch_sessions() returns None when Connection raises ConnectionRefusedError."""
        with patch(
            "iterm2.connection.Connection.run_until_complete",
            side_effect=ConnectionRefusedError("iTerm2 not running"),
        ):
            result = fetch_sessions()

        assert result is None

    def test_fetch_sessions_returns_none_on_any_exception(self):
        """fetch_sessions() returns None when Connection raises any other Exception."""
        with patch(
            "iterm2.connection.Connection.run_until_complete",
            side_effect=RuntimeError("unexpected error"),
        ):
            result = fetch_sessions()

        assert result is None

    def test_fetch_sessions_defaults_none_variables_to_empty_string(self):
        """session variables that return None are defaulted to empty string."""
        session = MagicMock()
        session.session_id = "w0t0p0:xyz"
        session.name = "NullSession"

        async def _async_get_variable(var_name: str):
            return None  # simulate unset variables

        session.async_get_variable = _async_get_variable

        mock_app = _make_mock_app([session])

        def run_until_complete(coro_fn, retry=False):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(coro_fn(MagicMock()))
            finally:
                loop.close()

        with (
            patch("iterm2.async_get_app", AsyncMock(return_value=mock_app)),
            patch(
                "iterm2.connection.Connection.run_until_complete",
                side_effect=run_until_complete,
            ),
        ):
            result = fetch_sessions()

        assert result is not None
        assert len(result) == 1
        ts = result[0]
        assert ts.foreground_process == ""
        assert ts.cwd == ""


# ---------------------------------------------------------------------------
# activate_session tests
# ---------------------------------------------------------------------------


class TestActivateSession:
    def test_activate_session_returns_true_when_session_found(self):
        """activate_session returns True when session found and activated."""
        mock_session = _make_mock_session(session_id="w0t0p0:abc")
        mock_app = _make_mock_app([], session_by_id={"w0t0p0:abc": mock_session})

        def run_until_complete(coro_fn, retry=False):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(coro_fn(MagicMock()))
            finally:
                loop.close()

        with (
            patch("iterm2.async_get_app", AsyncMock(return_value=mock_app)),
            patch(
                "iterm2.connection.Connection.run_until_complete",
                side_effect=run_until_complete,
            ),
        ):
            result = activate_session("w0t0p0:abc")

        assert result is True
        mock_session.async_activate.assert_called_once_with(
            select_tab=True, order_window_front=True
        )
        mock_app.async_activate.assert_called_once()

    def test_activate_session_returns_false_when_session_not_found(self):
        """activate_session returns False when get_session_by_id returns None."""
        mock_app = _make_mock_app([], session_by_id={})

        def run_until_complete(coro_fn, retry=False):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(coro_fn(MagicMock()))
            finally:
                loop.close()

        with (
            patch("iterm2.async_get_app", AsyncMock(return_value=mock_app)),
            patch(
                "iterm2.connection.Connection.run_until_complete",
                side_effect=run_until_complete,
            ),
        ):
            result = activate_session("nonexistent-id")

        assert result is False

    def test_activate_session_returns_false_on_exception(self):
        """activate_session returns False when Connection raises Exception."""
        with patch(
            "iterm2.connection.Connection.run_until_complete",
            side_effect=OSError("connection failed"),
        ):
            result = activate_session("some-session-id")

        assert result is False


# ---------------------------------------------------------------------------
# _SHELL_PROCESSES tests
# ---------------------------------------------------------------------------


class TestShellProcesses:
    def test_shell_processes_contains_zsh(self):
        """_SHELL_PROCESSES frozenset contains 'zsh'."""
        assert "zsh" in _SHELL_PROCESSES

    def test_shell_processes_contains_bash(self):
        """_SHELL_PROCESSES frozenset contains 'bash'."""
        assert "bash" in _SHELL_PROCESSES

    def test_shell_processes_contains_fish(self):
        """_SHELL_PROCESSES frozenset contains 'fish'."""
        assert "fish" in _SHELL_PROCESSES

    def test_shell_processes_is_frozenset(self):
        """_SHELL_PROCESSES is a frozenset (immutable)."""
        assert isinstance(_SHELL_PROCESSES, frozenset)
