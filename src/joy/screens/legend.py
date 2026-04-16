"""Icon legend modal: shows a reference of all icons used in joy's panes."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from joy.widgets.object_row import PRESET_ICONS
from joy.widgets.icons import (
    ICON_BRANCH, ICON_TICKET, ICON_THREAD, ICON_NOTE, ICON_TERMINAL, ICON_WORKTREE,
    ICON_MR_OPEN, ICON_MR_DRAFT, ICON_MR_CLOSED,
    ICON_CI_PASS, ICON_CI_FAIL, ICON_CI_PENDING,
    ICON_DIRTY, ICON_NO_UPSTREAM,
)
from joy.models import PresetKind


# (markup_icon, label) — icon string may contain Rich markup for color
_PROJECT_STATUS: list[tuple[str, str]] = [
    ("[green]\u25cf[/green]", "Priority  (g to cycle)"),
    ("[dim]\u25cf[/dim]",     "On hold   (g to cycle)"),
    ("[dim]\u25cb[/dim]",     "Idle      (g to cycle)"),
]

# Ribbon icons shown in cyan when the object is present, grey when absent
_PROJECT_RIBBON: list[tuple[str, str]] = [
    (f"[cyan]{ICON_BRANCH}[/cyan]",   "Branch"),
    (f"[cyan]{ICON_TICKET}[/cyan]",   "Ticket"),
    (f"[cyan]{ICON_THREAD}[/cyan]",   "Thread"),
    (f"[cyan]{ICON_NOTE}[/cyan]",     "Note"),
    (f"[cyan]{ICON_TERMINAL}[/cyan]", "Terminal"),
    (f"[cyan]{ICON_WORKTREE}[/cyan]", "Worktree"),
]

# MR strip icons (shown when project has a linked MR)
_PROJECT_MR: list[tuple[str, str]] = [
    (f"[green]{ICON_MR_OPEN}[/green]",   "MR open"),
    (f"[dim]{ICON_MR_DRAFT}[/dim]",      "MR draft"),
    (f"[dim]{ICON_MR_CLOSED}[/dim]",     "MR closed / merged"),
    (f"[green]{ICON_CI_PASS}[/green]",   "CI passed"),
    (f"[red]{ICON_CI_FAIL}[/red]",       "CI failed"),
    (f"[yellow]{ICON_CI_PENDING}[/yellow]", "CI pending"),
]

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
    (PRESET_ICONS.get(PresetKind.TERMINALS, ""), "Terminals", ""),
    (PRESET_ICONS.get(PresetKind.URL, ""), "URL", ""),
]

_INDICATOR_ICONS: list[tuple[str, str, str]] = [
    ("\u25cf", "Open by default", "filled circle"),
    ("\u25cb", "Not open by default", "empty circle"),
]

_WORKTREE_ICONS: list[tuple[str, str]] = [
    (f"[yellow]{ICON_DIRTY}[/yellow]",         "Uncommitted changes"),
    (f"[dim]{ICON_NO_UPSTREAM}[/dim]",         "No upstream remote"),
    (f"[green]{ICON_MR_OPEN}[/green]",         "MR open"),
    (f"[dim]{ICON_MR_DRAFT}[/dim]",            "MR draft"),
    (f"[green]{ICON_CI_PASS}[/green]",         "CI passed"),
    (f"[red]{ICON_CI_FAIL}[/red]",             "CI failed"),
    (f"[yellow]{ICON_CI_PENDING}[/yellow]",    "CI pending"),
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
    LegendModal .legend-note {
        height: 1;
        padding: 0 1;
        color: $text-muted;
        text-style: italic;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Icon Legend", classes="legend-title")
            with VerticalScroll():
                yield Static("Project List — Status", classes="legend-section")
                for icon_markup, label in _PROJECT_STATUS:
                    yield Static(f"  {icon_markup}  {label}", classes="legend-row", markup=True)

                yield Static("Project List — Icon Ribbon", classes="legend-section")
                yield Static("  cyan = linked  /  grey = not linked", classes="legend-note")
                for icon_markup, label in _PROJECT_RIBBON:
                    yield Static(f"  {icon_markup}  {label}", classes="legend-row", markup=True)

                yield Static("Project List — MR Strip", classes="legend-section")
                for icon_markup, label in _PROJECT_MR:
                    yield Static(f"  {icon_markup}  {label}", classes="legend-row", markup=True)

                yield Static("Details Pane", classes="legend-section")
                for icon, label, _desc in _DETAIL_ICONS:
                    yield Static(f"  {icon}  {label}", classes="legend-row")

                yield Static("Details — Indicators", classes="legend-section")
                for icon, label, desc in _INDICATOR_ICONS:
                    suffix = f"  ({desc})" if desc else ""
                    yield Static(f"  {icon}  {label}{suffix}", classes="legend-row")

                yield Static("Worktrees Pane", classes="legend-section")
                for icon_markup, label in _WORKTREE_ICONS:
                    yield Static(f"  {icon_markup}  {label}", classes="legend-row", markup=True)

                yield Static("Terminal Pane", classes="legend-section")
                for icon, label, _style in _TERMINAL_ICONS:
                    yield Static(f"  {icon}  {label}", classes="legend-row")

    def action_dismiss_legend(self) -> None:
        """Dismiss the legend modal."""
        self.dismiss(None)
