"""Fetch active iTerm2 sessions via the Python API."""
from __future__ import annotations

import subprocess

from joy.models import TerminalSession

# Shell processes that indicate the shell is in the foreground (Claude is idle/paused).
_SHELL_PROCESSES = frozenset({"zsh", "bash", "fish", "sh", "dash"})


def _detect_claude(job: str, tty: str) -> bool:
    """Return True if this session is running Claude (active or paused/backgrounded).

    Uses two signals in order of cost:
    1. Foreground job name contains "claude" (case-insensitive) — fast, catches the
       common case where the binary is named "claude" or "Claude".
    2. TTY process list contains "claude" in any argument — catches the Node.js wrapper
       case where jobName is "node" but the script path includes "claude", and also
       catches paused/backgrounded Claude processes (Ctrl+Z).

    Session name is intentionally NOT used — too imprecise (any tab named "claude"
    would match, even if Claude is not running).
    """
    if "claude" in job.lower():
        return True
    return _tty_has_claude(tty)


def _tty_has_claude(tty: str) -> bool:
    """Check if any process running on *tty* has 'claude' in its command arguments.

    Runs `ps -t <tty> -o args=` synchronously. Safe to call from a background
    thread (fetch_sessions runs inside @work(thread=True)).
    """
    if not tty:
        return False
    try:
        tty_short = tty.removeprefix("/dev/")
        result = subprocess.run(
            ["ps", "-t", tty_short, "-o", "args="],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return any(
            "claude" in line.lower()
            for line in result.stdout.splitlines()
            if line.strip()
        )
    except Exception:
        return False


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

    # Collect raw data inside async context, then compute is_claude synchronously
    # after run_until_complete returns (subprocess calls must not block the event loop).
    raw: list[tuple[str, str, str, str, str]] = []  # (id, name, job, cwd, tty)

    async def _enumerate(connection):
        app = await iterm2.async_get_app(connection)
        for window in app.terminal_windows:
            for tab in window.tabs:
                for session in tab.sessions:
                    job = await session.async_get_variable("jobName") or ""
                    cwd = await session.async_get_variable("path") or ""
                    tty = await session.async_get_variable("tty") or ""
                    raw.append((session.session_id, session.name or "", job, cwd, tty))

    try:
        Connection().run_until_complete(_enumerate, retry=False)
    except Exception:
        return None

    results: list[TerminalSession] = []
    for session_id, name, job, cwd, tty in raw:
        results.append(
            TerminalSession(
                session_id=session_id,
                session_name=name,
                foreground_process=job,
                cwd=cwd,
                is_claude=_detect_claude(job, tty),
            )
        )
    return results


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
