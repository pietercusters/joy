"""Bottom-left pane: interactive terminal session display with cursor navigation.

Displays active iTerm2 sessions grouped by project tab. Each project with a linked
iTerm2 tab appears as a named group header; sessions not in any project tab appear
under an 'Other' header. Navigation via j/k/up/down, Enter activates the highlighted
session, Escape returns focus to projects pane.
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
INDICATOR_BUSY = "\u25cf"    # BLACK CIRCLE -- session running claude
INDICATOR_WAITING = "\u25cb" # WHITE CIRCLE -- session at shell prompt


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
        show_shortcut: bool = False,
        **kwargs,
    ) -> None:
        self.session_id = session.session_id
        self.session_name = session.session_name  # FOUND-04: identity field for cursor preservation
        # Store original data for potential re-rendering
        self._session = session
        self._is_claude = is_claude
        self._is_busy = is_busy
        self._show_shortcut = show_shortcut
        content = self._build_content(session, is_claude=is_claude, is_busy=is_busy, show_shortcut=show_shortcut)
        super().__init__(content, **kwargs)

    @staticmethod
    def _build_content(
        session: TerminalSession,
        *,
        is_claude: bool = False,
        is_busy: bool = False,
        show_shortcut: bool = False,
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

        if show_shortcut:
            t.append("  [h]", style="dim")

        return t


# ---------------------------------------------------------------------------
# TerminalPane: main interactive pane widget (D-01 through D-17)
# ---------------------------------------------------------------------------


class TerminalPane(Widget, can_focus=True):
    """Bottom-left pane: interactive terminal session list.

    Sessions are pushed via set_sessions(). When tab_groups is provided,
    sessions are grouped under their project's tab header; sessions not in any
    project tab appear under an 'Other' header. When tab_groups is None, all
    sessions fall into 'Other'. Cursor navigation via j/k/up/down, Enter
    activates highlighted session, Escape returns to projects pane.
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
        Binding("o", "focus_session", "Open", show=False),
        Binding("n", "new_session", "New", show=False),
        Binding("e", "rename_session", "Rename", show=False),
        Binding("d", "close_session", "Close", show=False),
        Binding("D", "force_close_session", "Force Close", show=False),
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
    TerminalPane:focus-within:not(.--dim-selection) SessionRow.--highlight {
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
    TerminalPane.--dim-selection SessionRow.--highlight {
        background: transparent;
        color: $text-muted;
        text-style: dim;
    }
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "terminal-pane")
        super().__init__(**kwargs)
        self._cursor: int = -1
        self._rows: list[SessionRow] = []
        self._is_dimmed: bool = False
        self._sessions_cache: list[TerminalSession] | None = None
        self._tab_groups_cache: list[tuple[str, str]] | None = None
        self.border_title = "Terminal"

    def compose(self) -> ComposeResult:
        """Yield initial loading placeholder."""
        yield _TerminalScroll(
            Static("Loading\u2026", classes="empty-state"),
            id="terminal-scroll",
        )

    async def set_sessions(
        self,
        sessions: list[TerminalSession] | None,
        tab_groups: list[tuple[str, str]] | None = None,
    ) -> None:
        """Populate the pane with session rows. Idempotent.

        Args:
            sessions: List of TerminalSession objects, or None if iTerm2 is unavailable.
            tab_groups: List of (project_name, tab_id) pairs in display order. Sessions
                whose tab_id matches are grouped under the project's header. Sessions
                with no matching tab_id fall under 'Other'. None treats all as 'Other'.
        """
        self._sessions_cache = sessions
        self._tab_groups_cache = tab_groups
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

        def _sort_key(s: TerminalSession) -> tuple[int, int, str]:
            """Sort key: Claude-busy first (0,0), Claude-waiting (0,1), other (1,x), then alpha."""
            is_busy = s.foreground_process.lower() not in _SHELL_PROCESSES
            if s.is_claude:
                return (0, 0 if is_busy else 1, s.session_name.lower())
            return (1, 0, s.session_name.lower())

        new_rows: list[SessionRow] = []
        first_group = True

        if tab_groups:
            # Build tab_id -> project_name lookup
            tab_id_to_project: dict[str, str] = {tab_id: name for name, tab_id in tab_groups}
            project_tab_ids: set[str] = set(tab_id_to_project.keys())

            # Bucket sessions into per-project lists and other
            project_sessions: dict[str, list[TerminalSession]] = {name: [] for name, _ in tab_groups}
            other_sessions: list[TerminalSession] = []
            for session in sessions:
                if session.tab_id and session.tab_id in project_tab_ids:
                    project_sessions[tab_id_to_project[session.tab_id]].append(session)
                else:
                    other_sessions.append(session)

            # Mount project groups in tab_groups order (skip empty groups)
            for project_name, _tab_id in tab_groups:
                group = project_sessions[project_name]
                if not group:
                    continue
                if not first_group:
                    scroll.mount(Static("", classes="section-spacer"))
                first_group = False
                scroll.mount(GroupHeader(project_name))
                group.sort(key=_sort_key)
                for session in group:
                    is_busy = session.foreground_process.lower() not in _SHELL_PROCESSES
                    row = SessionRow(session, is_claude=session.is_claude, is_busy=is_busy, show_shortcut=len(new_rows) == 0)
                    scroll.mount(row)
                    new_rows.append(row)
        else:
            # No tab grouping data: all sessions go to Other
            other_sessions = list(sessions)

        # Mount Other group for sessions not in any project tab
        if other_sessions:
            if not first_group:
                scroll.mount(Static("", classes="section-spacer"))
            scroll.mount(GroupHeader("Other"))
            other_sessions.sort(key=_sort_key)
            for session in other_sessions:
                is_busy = session.foreground_process.lower() not in _SHELL_PROCESSES
                row = SessionRow(session, is_claude=session.is_claude, is_busy=is_busy, show_shortcut=len(new_rows) == 0)
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
        self._update_highlight(emit=False)  # refresh restore -- no sync message

        scroll.call_after_refresh(lambda: scroll.scroll_to(y=saved_scroll_y, animate=False))

    def _update_highlight(self, *, emit: bool = True) -> None:
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

    def sync_to(self, session_name: str) -> bool:
        """Move cursor to matching session_name row without posting SessionHighlighted.

        Silent cursor mutation for cross-pane sync. Does NOT call .focus(). (D-09, D-10)
        Returns True if a match was found, False otherwise. (D-08)
        """
        for i, row in enumerate(self._rows):
            if row.session_name == session_name:
                self._cursor = i
                for r in self._rows:
                    r.remove_class("--highlight")
                row.add_class("--highlight")
                row.scroll_visible()
                return True
        # No match: leave _cursor unchanged (D-08)
        return False

    def set_dimmed(self, dimmed: bool) -> None:
        """Set dimmed selection state (no project match). Adds/removes --dim-selection CSS class."""
        self._is_dimmed = dimmed
        if dimmed:
            self.add_class("--dim-selection")
        else:
            self.remove_class("--dim-selection")

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
        if self._is_dimmed:
            self.app.notify("No terminal for this project", markup=False)
            return
        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        session_id = self._rows[self._cursor].session_id
        self._do_activate(session_id)

    @work(thread=True, exit_on_error=False)
    def _do_activate(self, session_id: str) -> None:
        """Run activate_session in background thread to avoid blocking TUI (T-12-04)."""
        import joy.terminal_sessions as _ts  # noqa: PLC0415 -- lazy import; module ref for mockability
        _ts.activate_session(session_id)

    def action_focus_projects(self) -> None:
        """Return focus to the projects pane (D-13)."""
        self.app.query_one("#project-list").focus()

    # ------------------------------------------------------------------
    # n/e/d/D session management bindings
    # ------------------------------------------------------------------

    def action_new_session(self) -> None:
        """Create a new named terminal session (n key)."""
        from joy.screens import NameInputModal  # noqa: PLC0415

        def on_name(name: str | None) -> None:
            if name is None:
                return
            self._do_create_session(name)

        self.app.push_screen(
            NameInputModal(title="New Terminal Session", placeholder="Session name"),
            on_name,
        )

    @work(thread=True, exit_on_error=False)
    def _do_create_session(self, name: str) -> None:
        import joy.terminal_sessions as _ts  # noqa: PLC0415
        session_id = _ts.create_session(name)
        if session_id:
            self.app.call_from_thread(self.app.notify, f"Created session: {name}", markup=False)
            # Trigger refresh to pick up new session
            self.app.call_from_thread(self.app._load_terminal)
        else:
            self.app.call_from_thread(self.app.notify, "Failed to create session", severity="error", markup=False)

    def action_rename_session(self) -> None:
        """Rename the highlighted session (e key)."""
        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        row = self._rows[self._cursor]
        from joy.screens import NameInputModal  # noqa: PLC0415

        def on_name(new_name: str | None) -> None:
            if new_name is None:
                return
            self._do_rename_session(row.session_id, new_name)

        self.app.push_screen(
            NameInputModal(title="Rename Session", initial_value=row.session_name, placeholder="Session name"),
            on_name,
        )

    @work(thread=True, exit_on_error=False)
    def _do_rename_session(self, session_id: str, new_name: str) -> None:
        import joy.terminal_sessions as _ts  # noqa: PLC0415
        ok = _ts.rename_session(session_id, new_name)
        if ok:
            self.app.call_from_thread(self.app.notify, f"Renamed session", markup=False)
            # Trigger refresh to rebuild pane with new name
            self.app.call_from_thread(self.app._load_terminal)
        else:
            self.app.call_from_thread(self.app.notify, "Failed to rename session", severity="error", markup=False)

    def action_close_session(self) -> None:
        """Close the highlighted session with confirmation (d key)."""
        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        row = self._rows[self._cursor]
        # Capture by value before pushing modal — row may be replaced by a background refresh
        # before the user confirms, causing the closure to reference stale widget state (WR-02).
        session_id = row.session_id
        session_name = row.session_name
        from joy.screens import ConfirmationModal  # noqa: PLC0415

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            self._do_close_session(session_id, session_name, force=False)

        self.app.push_screen(
            ConfirmationModal("Close Session", f"Close '{session_name}'?", hint="Enter to close, Escape to cancel"),
            on_confirm,
        )

    @work(thread=True, exit_on_error=False)
    def _do_close_session(self, session_id: str, name: str, *, force: bool) -> None:
        import joy.terminal_sessions as _ts  # noqa: PLC0415
        ok = _ts.close_session(session_id, force=force)
        if ok:
            self.app.call_from_thread(self.app.notify, f"Closed session: {name}", markup=False)
            self.app.call_from_thread(self.app._load_terminal)
        else:
            # Graceful close failed -- offer force close
            if not force:
                self.app.call_from_thread(self._offer_force_close, session_id, name)
            else:
                self.app.call_from_thread(self.app.notify, f"Failed to close: {name}", severity="error", markup=False)

    def _offer_force_close(self, session_id: str, name: str) -> None:
        """Push force-close confirmation after graceful close fails."""
        from joy.screens import ConfirmationModal  # noqa: PLC0415

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            self._do_close_session(session_id, name, force=True)

        self.app.push_screen(
            ConfirmationModal(
                "Force Close Session",
                f"Force close '{name}'? (running processes will be killed)",
                hint="Enter to force close, Escape to cancel",
            ),
            on_confirm,
        )

    def action_force_close_session(self) -> None:
        """Force-close the highlighted session with confirmation (D key)."""
        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        row = self._rows[self._cursor]
        # Capture by value before pushing modal — row may be replaced by a background refresh.
        session_id = row.session_id
        session_name = row.session_name
        from joy.screens import ConfirmationModal  # noqa: PLC0415

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            self._do_close_session(session_id, session_name, force=True)

        self.app.push_screen(
            ConfirmationModal(
                "Force Close Session",
                f"Force close '{session_name}'?",
                hint="Enter to force close, Escape to cancel",
            ),
            on_confirm,
        )

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
