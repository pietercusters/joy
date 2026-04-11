"""Right pane: full project detail widget with grouped objects and cursor navigation."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.object_row import ObjectRow, _success_message, _truncate

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
        Binding("o", "open_object", "Open"),
        Binding("space", "toggle_default", "Toggle"),
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
        """Update the displayed project: rebuild grouped object rows and reset cursor.

        Defers DOM manipulation via call_after_refresh to ensure VerticalScroll is
        fully attached before mounting children into it.

        A generation counter guards against stale renders during rapid project
        switching: if set_project is called again before the deferred callback fires,
        the superseded render is a no-op.
        """
        self._project = project
        self._render_generation = getattr(self, "_render_generation", 0) + 1
        gen = self._render_generation
        self.call_after_refresh(lambda: self._render_project(gen))

    def _render_project(self, gen: int = 0) -> None:
        """Rebuild the grouped object rows for the current project.

        Args:
            gen: The render generation this callback was issued for. If it no longer
                 matches the current generation, this render has been superseded and
                 is skipped.
        """
        if gen != getattr(self, "_render_generation", 0):
            return  # superseded by a newer set_project call
        if self._project is None:
            return
        scroll = self.query_one("#detail-scroll", VerticalScroll)

        # Clear existing content
        scroll.remove_children()

        # Group objects by preset kind in defined display order
        grouped: dict[PresetKind, list[ObjectItem]] = {}
        for item in self._project.objects:
            grouped.setdefault(item.kind, []).append(item)

        # Mount groups in order, only for kinds that have objects
        new_rows: list[ObjectRow] = []
        row_index = 0
        for kind in GROUP_ORDER:
            items = grouped.get(kind, [])
            if not items:
                continue
            scroll.mount(GroupHeader(GROUP_LABELS[kind]))
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

    def action_open_object(self) -> None:
        """Open the highlighted object via operations.open_object (ACT-01, per D-09)."""
        item = self.highlighted_object
        if item is None:
            self.app.notify("No object selected", severity="error", markup=False)
            return
        self._do_open(item)

    @work(thread=True, exit_on_error=False)
    def _do_open(self, item: ObjectItem) -> None:
        """Run open_object in background thread to avoid blocking TUI."""
        from joy.operations import open_object  # noqa: PLC0415
        try:
            open_object(item=item, config=self.app._config)
            self.app.notify(
                _success_message(item, self.app._config),
                markup=False,
            )
        except Exception:
            display = _truncate(item.label if item.label else item.value)
            self.app.notify(f"Failed to open: {display}", severity="error", markup=False)

    def action_toggle_default(self) -> None:
        """Toggle open_by_default on highlighted object (ACT-03, per D-09, D-12)."""
        item = self.highlighted_object
        if item is None:
            return
        item.open_by_default = not item.open_by_default
        # Update the row's dot indicator in-place
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].refresh_indicator()
        # Persist in background
        self._save_toggle()

    @work(thread=True, exit_on_error=False)
    def _save_toggle(self) -> None:
        """Persist toggle change to TOML in background thread (D-12)."""
        from joy.store import save_projects  # noqa: PLC0415
        if hasattr(self.app, "_projects"):
            save_projects(self.app._projects)

    @property
    def highlighted_object(self) -> ObjectItem | None:
        """Return the currently highlighted ObjectItem, or None if no cursor."""
        if self._project and 0 <= self._cursor < len(self._rows):
            return self._rows[self._cursor].item
        return None
