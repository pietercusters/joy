"""LegendModal: icon legend popup showing all icons used across all panes."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static


class LegendModal(ModalScreen[None]):
    """Modal popup showing icon legend for all panes.

    Opened by pressing 'l' anywhere in the app. Dismissed by pressing
    Escape or 'l' again.
    """

    BINDINGS = [
        ("escape", "dismiss_legend", "Close"),
        ("l", "dismiss_legend", "Close"),
    ]

    DEFAULT_CSS = """
    LegendModal {
        align: center middle;
    }
    LegendModal > Vertical {
        width: 70;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $background 80%;
        padding: 1 2;
    }
    LegendModal .modal-title {
        text-style: bold;
        padding-bottom: 1;
    }
    LegendModal .section-header {
        text-style: bold;
        color: $text-muted;
        padding-top: 1;
    }
    LegendModal .icon-row {
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Icon Legend", classes="modal-title")
            yield VerticalScroll(
                *self._build_legend_content(),
                id="legend-scroll",
            )

    def _build_legend_content(self) -> list[Static]:
        """Build the full icon legend as a list of Static widgets."""
        widgets: list[Static] = []

        # --- Details Pane ---
        widgets.append(Static("Details Pane", classes="section-header"))
        for icon, desc, style in [
            ("\ue725", "Merge Request", ""),
            ("\ue0a0", "Branch", ""),
            ("\uf0ea", "Ticket", ""),
            ("\uf086", "Thread", ""),
            ("\uf15b", "File", ""),
            ("\uf040", "Note", ""),
            ("\uf07b", "Worktree", ""),
            ("\uf120", "Terminal / Agents", ""),
            ("\uf0ac", "URL", ""),
        ]:
            t = Text()
            t.append(f"  {icon}  ", style=style or "default")
            t.append(desc)
            widgets.append(Static(t, classes="icon-row"))

        # --- Worktree Pane ---
        widgets.append(Static("Worktree Pane", classes="section-header"))
        for icon, desc, style in [
            ("\ue0a0", "Branch name", "bold"),
            ("\uf111", "Uncommitted changes", "yellow"),
            ("\U000f0be1", "No upstream remote", "dim"),
            ("\uea64", "MR open", "green"),
            ("\uebdb", "MR draft", "dim"),
            ("\uf00c", "CI passed", "green"),
            ("\uf00d", "CI failed", "red"),
            ("\uf192", "CI pending", "yellow"),
        ]:
            t = Text()
            t.append(f"  {icon}  ", style=style)
            t.append(desc)
            widgets.append(Static(t, classes="icon-row"))

        # --- Terminal Pane ---
        widgets.append(Static("Terminal Pane", classes="section-header"))
        for icon, desc, style in [
            ("\uf120", "Terminal session", "bold"),
            ("\U000f1325", "Claude agent", "bold"),
            ("\u25cf", "Claude busy", "green"),
            ("\u25cb", "Claude waiting", "dim"),
        ]:
            t = Text()
            t.append(f"  {icon}  ", style=style)
            t.append(desc)
            widgets.append(Static(t, classes="icon-row"))

        return widgets

    def on_mount(self) -> None:
        """Focus the screen itself since there is no Input widget."""
        self.focus()

    def action_dismiss_legend(self) -> None:
        """Dismiss the legend modal."""
        self.dismiss(None)
