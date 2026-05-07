"""Bottom-right placeholder pane (position 6 in 3x2 grid)."""
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class PlaceholderPane(Widget, can_focus=False):
    """Empty placeholder pane. Non-focusable, skipped by Tab."""

    DEFAULT_CSS = """
    PlaceholderPane {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "placeholder-pane")
        super().__init__(**kwargs)
        self.border_title = ""

    def compose(self) -> ComposeResult:
        yield Static("", classes="empty-state")
