"""Bottom-left pane: terminal session placeholder (Phase 12 will fill this in)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class TerminalPane(Widget, can_focus=True):
    """Stub pane for terminal sessions. Focusable but no interactive keys (D-08, D-10)."""

    BINDINGS = []

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
    TerminalPane Static {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
    }
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "terminal-pane")
        super().__init__(**kwargs)
        self.border_title = "Terminal"

    def compose(self) -> ComposeResult:
        yield Static("coming soon")
