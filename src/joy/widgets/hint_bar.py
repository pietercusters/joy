"""Two-row keyboard hint bar replacing the default Textual Footer."""
from __future__ import annotations

from textual.app import RenderResult
from textual.reactive import reactive
from textual.widget import Widget


class HintBar(Widget):
    """Two-row keyboard hint bar. Row 1: pane-specific. Row 2: global."""

    DEFAULT_CSS = """
    HintBar {
        dock: bottom;
        height: 2;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    """

    pane_hints: reactive[str] = reactive("")
    global_hints: reactive[str] = reactive("")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.global_hints = (
            "b: Branch  m: MR  i: IDE  y: Ticket  u: Note  t: Thread  h: Terminal  "
            "O: Open all  s: Settings  r: Refresh  l: Legend  q: Quit  x: Sync"
        )

    def render(self) -> RenderResult:
        pane_line = self.pane_hints if self.pane_hints else ""
        return f"{pane_line}\n{self.global_hints}"
