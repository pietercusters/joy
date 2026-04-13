"""Fetch active iTerm2 sessions via the Python API."""
from __future__ import annotations

from joy.models import TerminalSession

# Shell processes that indicate an idle/waiting Claude session.
# Used by Plan 02 (TerminalPane) for Claude detection and display logic.
_SHELL_PROCESSES = frozenset({"zsh", "bash", "fish"})


def fetch_sessions() -> list[TerminalSession] | None:
    """Return all active iTerm2 sessions, or None if API unavailable.

    Uses Connection().run_until_complete() (instance method) to avoid
    the module-level function's sys.exit(1) on ConnectionRefusedError.
    Per D-02: runs in @work(thread=True) worker with its own event loop.
    Per D-03: catches all exceptions and returns None.

    All iterm2 imports are lazy (inside function body) to avoid import-time
    weight on startup. The iterm2 package is only imported when this function
    is called from a background worker thread.
    """
    import iterm2
    from iterm2.connection import Connection

    results: list[TerminalSession] = []

    async def _enumerate(connection):
        app = await iterm2.async_get_app(connection)
        for window in app.terminal_windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    job = await session.async_get_variable("jobName") or ""
                    cwd = await session.async_get_variable("path") or ""
                    results.append(
                        TerminalSession(
                            session_id=session.session_id,
                            session_name=session.name or "",
                            foreground_process=job,
                            cwd=cwd,
                        )
                    )

    try:
        Connection().run_until_complete(_enumerate, retry=False)
        return results
    except Exception:
        return None


def activate_session(session_id: str) -> bool:
    """Focus an iTerm2 session by ID. Returns True on success, False on failure.

    Per D-12: called from @work(thread=True) worker via asyncio in background thread.
    Brings the session's tab and iTerm2 app window to the front.

    All iterm2 imports are lazy to avoid startup overhead.
    """
    import iterm2
    from iterm2.connection import Connection

    success = False

    async def _focus(connection):
        nonlocal success
        app = await iterm2.async_get_app(connection)
        session = app.get_session_by_id(session_id)
        if session:
            await session.async_activate(select_tab=True, order_window_front=True)
            await app.async_activate()
            success = True

    try:
        Connection().run_until_complete(_focus, retry=False)
    except Exception:
        pass
    return success
