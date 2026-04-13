"""Bottom-right pane: worktree list placeholder (Phase 9 will fill this in)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class WorktreePane(Widget, can_focus=True):
    """Stub pane for worktree list. Focusable but no interactive keys (D-08, D-10)."""

    BINDINGS = []

    DEFAULT_CSS = """
    WorktreePane {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    WorktreePane:focus-within {
        border: solid $accent;
    }
    WorktreePane:focus {
        border: solid $accent;
    }
    WorktreePane Static {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
    }
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "worktrees-pane")
        super().__init__(**kwargs)
        self.border_title = "Worktrees"

    def compose(self) -> ComposeResult:
        yield Static("coming soon")
