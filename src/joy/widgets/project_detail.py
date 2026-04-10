"""Right pane: full project detail widget with grouped objects and cursor navigation."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.object_row import ObjectRow

# Display order for groups in the detail pane
GROUP_ORDER: list[PresetKind] = [
    PresetKind.WORKTREE,
    PresetKind.BRANCH,
    PresetKind.MR,
    PresetKind.TICKET,
    PresetKind.THREAD,
    PresetKind.FILE,
    PresetKind.NOTE,
    PresetKind.AGENTS,
    PresetKind.URL,
]

# Human-readable group header labels
GROUP_LABELS: dict[PresetKind, str] = {
    PresetKind.MR: "Merge Requests",
    PresetKind.BRANCH: "Branches",
    PresetKind.TICKET: "Tickets",
    PresetKind.THREAD: "Threads",
    PresetKind.FILE: "Files",
    PresetKind.NOTE: "Notes",
    PresetKind.WORKTREE: "Worktrees",
    PresetKind.AGENTS: "Agents",
    PresetKind.URL: "URLs",
}


class GroupHeader(Static):
    """Subtle header row separating object groups by preset type."""

    DEFAULT_CSS = """
    GroupHeader {
        width: 1fr;
        height: 1;
        color: $text-muted;
        text-style: bold;
        padding: 0 1;
    }
    """


class ProjectDetail(Widget, can_focus=True):
    """Right pane: shows project objects grouped by preset type with cursor navigation.

    j/k and up/down arrows move a cursor highlight through ObjectRow widgets.
    Escape returns focus to the project list.
    The highlighted_object property exposes the current item for Phase 3 activation.
    """

    BINDINGS = [
        Binding("escape", "focus_list", "Back"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("j", "cursor_down", "Down"),
    ]

    DEFAULT_CSS = """
    ProjectDetail {
        width: 1fr;
        height: 1fr;
        overflow-y: auto;
    }
    ProjectDetail > VerticalScroll {
        width: 1fr;
        height: 1fr;
    }
    ObjectRow.--highlight {
        background: $accent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._project: Project | None = None
        self._cursor: int = -1
        self._rows: list[ObjectRow] = []

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="detail-scroll")

    def set_project(self, project: Project) -> None:
        """Update the displayed project: rebuild grouped object rows and reset cursor."""
        self._project = project
        scroll = self.query_one("#detail-scroll", VerticalScroll)

        # Clear existing content
        scroll.remove_children()

        # Group objects by preset kind in defined display order
        grouped: dict[PresetKind, list[ObjectItem]] = {}
        for item in project.objects:
            grouped.setdefault(item.kind, []).append(item)

        # Mount groups in order, only for kinds that have objects
        new_rows: list[ObjectRow] = []
        row_index = 0
        for kind in GROUP_ORDER:
            items = grouped.get(kind, [])
            if not items:
                continue
            # Mount group header
            scroll.mount(GroupHeader(GROUP_LABELS[kind]))
            # Mount one ObjectRow per item
            for item in items:
                row = ObjectRow(item, index=row_index)
                scroll.mount(row)
                new_rows.append(row)
                row_index += 1

        self._rows = new_rows
        self._cursor = 0 if new_rows else -1
        self._update_highlight()

    def _update_highlight(self) -> None:
        """Apply the '--highlight' CSS class to the row at the current cursor position."""
        for row in self._rows:
            row.remove_class("--highlight")
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].add_class("--highlight")
            self._rows[self._cursor].scroll_visible()

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

    def action_focus_list(self) -> None:
        """Return focus to the project list (D-06, CORE-04)."""
        project_list = self.app.query_one("#project-list")
        listview = project_list.query_one("#project-listview")
        listview.focus()

    @property
    def highlighted_object(self) -> ObjectItem | None:
        """Return the currently highlighted ObjectItem, or None if no cursor."""
        if self._project and 0 <= self._cursor < len(self._rows):
            return self._rows[self._cursor].item
        return None
