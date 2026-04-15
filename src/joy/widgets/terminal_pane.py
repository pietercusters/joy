"""Bottom-left pane: interactive terminal session display with cursor navigation.

Displays active iTerm2 sessions grouped into Claude/Other groups.
Claude sessions (foreground_process=='claude') appear first under a 'Claude'
header; all others appear under an 'Other' header. Navigation via j/k/up/down,
Enter activates the highlighted session, Escape returns focus to projects pane.
"""
from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from joy.models import TerminalSession

# ---------------------------------------------------------------------------
# Nerd Font icon constants (per D-07)
# ---------------------------------------------------------------------------

ICON_SESSION = "\uf120"      # nf-fa-terminal
ICON_CLAUDE = "\U000f1325"   # nf-md-robot (AI/robot glyph)
INDICATOR_BUSY = "\u25cf"    # BLACK CIRCLE — session running claude
INDICATOR_WAITING = "\u25cb" # WHITE CIRCLE — session at shell prompt


# ---------------------------------------------------------------------------
# Pure helper: abbreviate home directory prefix (same pattern as worktree_pane.py)
# ---------------------------------------------------------------------------


def _abbreviate_home(path_str: str) -> str:
    """Replace leading home directory prefix with ~.

    Examples:
        /Users/pieter/Github/joy -> ~/Github/joy
        /Users/pieter             -> ~
        /tmp/other                -> /tmp/other (unchanged)
    """
    home = str(Path.home())
    if path_str.startswith(home):
        return "~" + path_str[len(home):]
    return path_str


# ---------------------------------------------------------------------------
# _TerminalScroll: non-focusable scroll container (per Pitfall 1 from RESEARCH.md)
# ---------------------------------------------------------------------------


class _TerminalScroll(VerticalScroll, can_focus=False):
    """Non-focusable scroll container for terminal session rows.

    Prevents VerticalScroll from stealing focus from TerminalPane
    (VerticalScroll is focusable by default).
    """


# ---------------------------------------------------------------------------
# GroupHeader: section header (duplicated from worktree_pane to avoid coupling)
# ---------------------------------------------------------------------------


class GroupHeader(Static):
    """Group section header. Duplicated from worktree_pane to avoid cross-widget coupling."""

    DEFAULT_CSS = """
    GroupHeader {
        width: 1fr;
        height: 1;
        color: $text-muted;
        text-style: bold;
        padding: 0 1;
    }
    """


# ---------------------------------------------------------------------------
# SessionRow: single-line row for one terminal session (D-05)
# ---------------------------------------------------------------------------


class SessionRow(Static):
    """Single-line row displaying one terminal session.

    Stores session_id for Enter key activation. Content format:
    [icon]  [session_name]  [busy/waiting indicator]  [process]  [cwd]
    """

    DEFAULT_CSS = """
    SessionRow {
        width: 1fr;
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        session: TerminalSession,
        *,
        is_claude: bool = False,
        is_busy: bool = False,
        **kwargs,
    ) -> None:
        self.session_id = session.session_id
        self.session_name = session.session_name  # FOUND-04: identity field for cursor preservation
        content = self._build_content(session, is_claude=is_claude, is_busy=is_busy)
        super().__init__(content, **kwargs)

    @staticmethod
    def _build_content(
        session: TerminalSession,
        *,
        is_claude: bool = False,
        is_busy: bool = False,
    ) -> Text:
        """Build the rich.Text renderable for a single-line session row."""
        t = Text(no_wrap=True, overflow="ellipsis")

        if is_claude:
            t.append(f" {ICON_CLAUDE} ", style="bold")
            t.append(session.session_name)
            if is_busy:
                t.append(f"  {INDICATOR_BUSY}", style="green")
            else:
                t.append(f"  {INDICATOR_WAITING}", style="dim")
            t.append(f"  {session.foreground_process}", style="dim")
        else:
            t.append(f" {ICON_SESSION} ", style="bold")
            t.append(session.session_name)
            t.append(f"  {session.foreground_process}", style="dim")

        # Abbreviated cwd
        cwd = _abbreviate_home(session.cwd)
        t.append(f"  {cwd}", style="dim")

        return t


# ---------------------------------------------------------------------------
# TerminalPane: main interactive pane widget (D-01 through D-17)
# ---------------------------------------------------------------------------


class TerminalPane(Widget, can_focus=True):
    """Bottom-left pane: interactive terminal session list.

    Sessions are pushed via set_sessions(). Claude sessions (foreground_process=='claude')
    are grouped under a 'Claude' header; others appear under 'Other'. Cursor navigation
    via j/k/up/down, Enter activates highlighted session, Escape returns to projects pane.
    """

    class SessionHighlighted(Message):
        """Fired when highlight moves to a different session row. (D-01, D-02)"""

        def __init__(self, session_name: str) -> None:
            self.session_name = session_name
            super().__init__()

    BINDINGS = [
        Binding("escape", "focus_projects", "Back"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("j", "cursor_down", "Down"),
        Binding("enter", "focus_session", "Focus"),
    ]

    DEFAULT_CSS = """
    TerminalPane {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    TerminalPane:focus-within {
        border: solid $accent;
    }
    TerminalPane:focus {
        border: solid $accent;
    }
    TerminalPane:focus-within SessionRow.--highlight {
        background: $accent;
    }
    SessionRow.--highlight {
        background: $accent 30%;
    }
    TerminalPane .empty-state {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
    }
    TerminalPane .section-spacer {
        height: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "terminal-pane")
        super().__init__(**kwargs)
        self._cursor: int = -1
        self._rows: list[SessionRow] = []
        self.border_title = "Terminal"

    def compose(self) -> ComposeResult:
        """Yield initial loading placeholder."""
        yield _TerminalScroll(
            Static("Loading\u2026", classes="empty-state"),
            id="terminal-scroll",
        )

    async def set_sessions(self, sessions: list[TerminalSession] | None) -> None:
        """Populate the pane with session rows. Idempotent.

        Args:
            sessions: List of TerminalSession objects, or None if iTerm2 is unavailable.
        """
        scroll = self.query_one("#terminal-scroll", _TerminalScroll)
        saved_scroll_y = scroll.scroll_y
        # FOUND-04: save cursor identity before DOM rebuild (D-12, D-13)
        saved_name: str | None = None
        saved_index = self._cursor
        if 0 <= self._cursor < len(self._rows):
            saved_name = self._rows[self._cursor].session_name
        await scroll.remove_children()

        if sessions is None:
            scroll.mount(Static("iTerm2 unavailable", classes="empty-state"))
            self._cursor = -1
            self._rows = []
            scroll.call_after_refresh(lambda: scroll.scroll_to(y=saved_scroll_y, animate=False))
            return

        if not sessions:
            scroll.mount(Static("No terminal sessions", classes="empty-state"))
            self._cursor = -1
            self._rows = []
            scroll.call_after_refresh(lambda: scroll.scroll_to(y=saved_scroll_y, animate=False))
            return

        from joy.terminal_sessions import _SHELL_PROCESSES  # noqa: PLC0415

        # Split into Claude sessions vs. other using the is_claude flag set at fetch time.
        # is_claude uses multi-signal detection: job name, session name, TTY process list.
        claude_sessions = [s for s in sessions if s.is_claude]
        other_sessions = [s for s in sessions if not s.is_claude]

        # Within Claude group: busy (Claude/node is foreground) sorts before waiting
        # (shell is foreground — Claude is paused/backgrounded), then alpha by name.
        def _claude_sort_key(s: TerminalSession) -> tuple[int, str]:
            is_busy = s.foreground_process.lower() not in _SHELL_PROCESSES
            return (0 if is_busy else 1, s.session_name.lower())

        claude_sessions.sort(key=_claude_sort_key)

        # Sort Other sessions alphabetically by session_name
        other_sessions.sort(key=lambda s: s.session_name.lower())

        new_rows: list[SessionRow] = []
        first_group = True

        # Mount Claude group (if any)
        if claude_sessions:
            first_group = False
            scroll.mount(GroupHeader("Claude"))
            for session in claude_sessions:
                is_busy = session.foreground_process.lower() not in _SHELL_PROCESSES
                row = SessionRow(session, is_claude=True, is_busy=is_busy)
                scroll.mount(row)
                new_rows.append(row)

        # Mount Other group (if any)
        if other_sessions:
            if not first_group:
                scroll.mount(Static("", classes="section-spacer"))
            first_group = False
            scroll.mount(GroupHeader("Other"))
            for session in other_sessions:
                row = SessionRow(session, is_claude=False)
                scroll.mount(row)
                new_rows.append(row)

        self._rows = new_rows
        # FOUND-04: restore cursor by session_name identity (D-13, D-14)
        if saved_name is not None and new_rows:
            for i, row in enumerate(new_rows):
                if row.session_name == saved_name:
                    self._cursor = i
                    break
            else:
                # Session gone: clamp to saved index (D-14)
                self._cursor = min(saved_index, len(new_rows) - 1)
        elif new_rows:
            self._cursor = 0
        else:
            self._cursor = -1
        self._update_highlight()

        scroll.call_after_refresh(lambda: scroll.scroll_to(y=saved_scroll_y, animate=False))

    def _update_highlight(self) -> None:
        """Apply '--highlight' CSS class to the row at the current cursor position."""
        for row in self._rows:
            row.remove_class("--highlight")
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].add_class("--highlight")
            self._rows[self._cursor].scroll_visible()
            # Post message only when not in a sync operation (D-03, Pitfall 1 prevention)
            if not getattr(self.app, "_is_syncing", False):
                self.post_message(
                    self.SessionHighlighted(self._rows[self._cursor].session_name)
                )

    def sync_to(self, session_name: str) -> None:
        """Move cursor to matching session_name row without posting SessionHighlighted.

        Silent cursor mutation for cross-pane sync. Does NOT call .focus(). (D-09, D-10)
        If no row matches, _cursor is left unchanged. (D-08)
        """
        for i, row in enumerate(self._rows):
            if row.session_name == session_name:
                self._cursor = i
                for r in self._rows:
                    r.remove_class("--highlight")
                row.add_class("--highlight")
                row.scroll_visible()
                return
        # No match: leave _cursor unchanged (D-08)

    def action_cursor_up(self) -> None:
        """Move cursor up one row."""
        if self._cursor > 0:
            self._cursor -= 1
            self._update_highlight()

    def action_cursor_down(self) -> None:
        """Move cursor down one row."""
        if self._cursor < len(self._rows) - 1:
            self._cursor += 1
            self._update_highlight()

    def action_focus_session(self) -> None:
        """Activate the highlighted session (D-12). No-op if cursor is invalid."""
        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        session_id = self._rows[self._cursor].session_id
        self._do_activate(session_id)

    @work(thread=True, exit_on_error=False)
    def _do_activate(self, session_id: str) -> None:
        """Run activate_session in background thread to avoid blocking TUI (T-12-04)."""
        import joy.terminal_sessions as _ts  # noqa: PLC0415 — lazy import; module ref for mockability
        _ts.activate_session(session_id)

    def action_focus_projects(self) -> None:
        """Return focus to the projects pane (D-13)."""
        self.app.query_one("#project-list").focus()

    def set_refresh_label(self, timestamp: str, *, stale: bool = False) -> None:
        """Update border_title with refresh timestamp. stale adds warning icon (D-16).

        Args:
            timestamp: Human-readable time string (e.g., "2m ago", "14:32").
            stale: If True, prefix timestamp with warning icon (U+26A0).
        """
        parts = ["Terminal"]
        if stale:
            parts.append("\u26a0")
        parts.append(timestamp)
        self.border_title = "  ".join(parts)
