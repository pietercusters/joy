"""Icon legend modal: shows a reference of all icons used in joy's panes."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from joy.widgets.object_row import PRESET_ICONS
from joy.models import PresetKind


# (icon, label, description) tuples for each section
_DETAIL_ICONS: list[tuple[str, str, str]] = [
    (PRESET_ICONS.get(PresetKind.REPO, ""), "Repository", ""),
    (PRESET_ICONS.get(PresetKind.MR, ""), "Merge Request", ""),
    (PRESET_ICONS.get(PresetKind.BRANCH, ""), "Branch", ""),
    (PRESET_ICONS.get(PresetKind.TICKET, ""), "Ticket", ""),
    (PRESET_ICONS.get(PresetKind.THREAD, ""), "Thread", ""),
    (PRESET_ICONS.get(PresetKind.FILE, ""), "File", ""),
    (PRESET_ICONS.get(PresetKind.NOTE, ""), "Note", ""),
    (PRESET_ICONS.get(PresetKind.WORKTREE, ""), "Worktree", ""),
    (PRESET_ICONS.get(PresetKind.AGENTS, ""), "Agents", ""),
    (PRESET_ICONS.get(PresetKind.URL, ""), "URL", ""),
]

_INDICATOR_ICONS: list[tuple[str, str, str]] = [
    ("\u25cf", "Open by default", "filled circle"),
    ("\u25cb", "Not open by default", "empty circle"),
]

_WORKTREE_ICONS: list[tuple[str, str, str]] = [
    ("\uf111", "Uncommitted changes", "yellow"),
    ("\U000f0be1", "No upstream remote", "dim"),
    ("\uea64", "MR open", "green"),
    ("\uebdb", "MR draft", "dim"),
    ("\uf00c", "CI passed", "green"),
    ("\uf00d", "CI failed", "red"),
    ("\uf192", "CI pending", "yellow"),
]

_TERMINAL_ICONS: list[tuple[str, str, str]] = [
    ("\uf120", "Terminal session", ""),
    ("\U000f1325", "Claude agent session", ""),
    ("\u25cf", "Claude busy (running)", "green"),
    ("\u25cb", "Claude waiting (at prompt)", "dim"),
]


class LegendModal(ModalScreen[None]):
    """Modal overlay showing icon legend for all panes."""

    BINDINGS = [
        Binding("escape", "dismiss_legend", "Close"),
        Binding("l", "dismiss_legend", "Close"),
    ]

    DEFAULT_CSS = """
    LegendModal {
        align: center middle;
    }
    LegendModal > Vertical {
        width: 60;
        max-height: 80%;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    LegendModal .legend-title {
        text-style: bold;
        width: 1fr;
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
    }
    LegendModal .legend-section {
        text-style: bold;
        color: $text-muted;
        height: 1;
        margin-top: 1;
    }
    LegendModal .legend-row {
        height: 1;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Icon Legend", classes="legend-title")
            with VerticalScroll():
                yield Static("Details Pane", classes="legend-section")
                for icon, label, _desc in _DETAIL_ICONS:
                    yield Static(f"  {icon}  {label}", classes="legend-row")

                yield Static("Details — Indicators", classes="legend-section")
                for icon, label, desc in _INDICATOR_ICONS:
                    suffix = f"  ({desc})" if desc else ""
                    yield Static(f"  {icon}  {label}{suffix}", classes="legend-row")

                yield Static("Worktrees Pane", classes="legend-section")
                for icon, label, _style in _WORKTREE_ICONS:
                    yield Static(f"  {icon}  {label}", classes="legend-row")

                yield Static("Terminal Pane", classes="legend-section")
                for icon, label, _style in _TERMINAL_ICONS:
                    yield Static(f"  {icon}  {label}", classes="legend-row")

    def action_dismiss_legend(self) -> None:
        """Dismiss the legend modal."""
        self.dismiss(None)
