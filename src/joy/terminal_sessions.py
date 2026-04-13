"""iTerm2 terminal session management. Async API calls wrapped for sync use.

This module provides fetch_sessions() and activate_session() for use
with the TerminalPane widget.

Note: This is the stub created by Plan 12-02. Plan 12-01 will provide
the full implementation with iterm2 API integration. This stub provides
the minimal interface for testing Plan 12-02's TerminalPane widget.
"""
from __future__ import annotations

from joy.models import TerminalSession

# Shell processes that indicate a session is idle (waiting for input)
_SHELL_PROCESSES: frozenset[str] = frozenset({"zsh", "bash", "fish"})


def fetch_sessions() -> list[TerminalSession] | None:
    """Fetch all iTerm2 sessions.

    Returns:
        List of TerminalSession objects, or None if iTerm2 is unavailable.
    """
    try:
        import iterm2  # type: ignore[import]
    except ImportError:
        return None
    # Full implementation in Plan 12-01
    return None


def activate_session(session_id: str) -> bool:
    """Activate the iTerm2 session with the given session_id.

    Args:
        session_id: The iTerm2 session identifier.

    Returns:
        True if successful, False if session not found or iTerm2 unavailable.
    """
    try:
        import iterm2  # type: ignore[import]
    except ImportError:
        return False
    # Full implementation in Plan 12-01
    return False
