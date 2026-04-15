"""Right pane: full project detail widget with grouped objects and cursor navigation."""
from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static


class _DetailScroll(VerticalScroll, can_focus=False):
    """Non-focusable scroll container for the detail pane.

    VerticalScroll is focusable by default. Making it non-focusable prevents it
    from stealing focus from ProjectDetail after a DOM rebuild, which would cause
    the e/d/o bindings on ProjectDetail to silently fail.
    """

from joy.models import ObjectItem, PresetKind, Project
from joy.widgets.object_row import KIND_SHORTCUT, ObjectRow, _success_message, _truncate

# Semantic group structure for Details pane
SEMANTIC_GROUPS: list[tuple[str, list[PresetKind]]] = [
    ("Code", [PresetKind.REPO, PresetKind.WORKTREE, PresetKind.MR, PresetKind.BRANCH]),
    ("Docs", [PresetKind.TICKET, PresetKind.NOTE, PresetKind.URL, PresetKind.FILE, PresetKind.THREAD]),
    ("Agents", [PresetKind.AGENTS]),
]


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
        Binding("n", "add_object", "Add"),
        Binding("e", "edit_object", "Edit"),
        Binding("d", "delete_object", "Delete"),
        Binding("D", "force_delete_object", "Force Delete"),
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
    ProjectDetail:focus-within ObjectRow.--highlight {
        background: $accent;
    }
    ObjectRow.--highlight {
        background: $accent 30%;
    }
    .section-spacer {
        height: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._project: Project | None = None
        self._cursor: int = -1
        self._rows: list[ObjectRow] = []
        self.border_title = "Details"

    def compose(self) -> ComposeResult:
        yield _DetailScroll(id="detail-scroll")

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

    def _render_project(self, gen: int = 0, *, initial_cursor: int | None = None) -> None:
        """Rebuild the grouped object rows for the current project.

        Args:
            gen: The render generation this callback was issued for. If it no longer
                 matches the current generation, this render has been superseded and
                 is skipped.
            initial_cursor: If provided, set cursor to this position (clamped to valid
                 range) instead of the default 0. Used for post-delete cursor restore.
        """
        if gen != getattr(self, "_render_generation", 0):
            return  # superseded by a newer set_project call
        if self._project is None:
            return
        scroll = self.query_one("#detail-scroll", _DetailScroll)

        # Clear existing content
        scroll.remove_children()

        # Group objects by preset kind in defined display order
        grouped: dict[PresetKind, list[ObjectItem]] = {}
        for item in self._project.objects:
            grouped.setdefault(item.kind, []).append(item)

        # Synthesize repo ObjectItem if project has a repo URL
        if self._project.repo:
            repo_item = ObjectItem(kind=PresetKind.REPO, value=self._project.repo, label="")
            grouped.setdefault(PresetKind.REPO, []).append(repo_item)

        # Mount semantic groups, only for groups that have objects
        new_rows: list[ObjectRow] = []
        row_index = 0
        first_group = True
        shortcut_kinds_shown: set[PresetKind] = set()
        for group_label, kinds in SEMANTIC_GROUPS:
            group_items: list[ObjectItem] = []
            for kind in kinds:
                group_items.extend(grouped.get(kind, []))
            if not group_items:
                continue
            if not first_group:
                scroll.mount(Static("", classes="section-spacer"))
            first_group = False
            scroll.mount(GroupHeader(group_label))
            for item in group_items:
                show_sc = item.kind in KIND_SHORTCUT and item.kind not in shortcut_kinds_shown
                if show_sc:
                    shortcut_kinds_shown.add(item.kind)
                row = ObjectRow(item, index=row_index, show_shortcut=show_sc)
                if getattr(item, 'stale', False):
                    row.add_class("--stale")
                scroll.mount(row)
                new_rows.append(row)
                row_index += 1

        self._rows = new_rows
        if initial_cursor is not None:
            self._cursor = max(0, min(initial_cursor, len(new_rows) - 1)) if new_rows else -1
        else:
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
        self.app.query_one("#project-list").focus()

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

    def action_add_object(self) -> None:
        """Open add-object flow for current project (MGMT-01, D-05, D-07)."""
        if self._project is None:
            return
        self.app._start_add_object_loop(self._project)

    def _set_project_with_cursor(self, project: Project, cursor: int) -> None:
        """Re-render project and restore cursor near given position."""
        self._project = project
        self._render_generation = getattr(self, "_render_generation", 0) + 1
        gen = self._render_generation
        self.call_after_refresh(lambda: self._render_project(gen, initial_cursor=cursor))

    def action_edit_object(self) -> None:
        """Open edit modal for highlighted object (MGMT-02, D-08, D-09)."""
        from joy.screens import ValueInputModal  # noqa: PLC0415 — lazy import avoids circular dep
        item = self.highlighted_object
        if item is None:
            self.app.notify("No object selected", severity="error", markup=False)
            return
        kind = item.kind

        def on_value(new_value: str | None) -> None:
            if new_value is None:
                return  # Escape — no change
            item.value = new_value
            self._save_toggle()  # reuse existing bg save method (same as toggle persist)
            self.set_project(self._project)  # re-render to show updated value
            display = _truncate(new_value)
            self.app.notify(f"Updated: {kind.value} '{display}'", markup=False)

        self.app.push_screen(
            ValueInputModal(kind, existing_value=item.value),
            on_value,
        )

    def action_delete_object(self) -> None:
        """Delete highlighted object after confirmation (MGMT-03, D-10, D-11)."""
        from joy.screens import ConfirmationModal  # noqa: PLC0415 — lazy import avoids circular dep
        item = self.highlighted_object
        if item is None:
            self.app.notify("No object selected", severity="error", markup=False)
            return
        kind_val = item.kind.value
        value_display = _truncate(item.label if item.label else item.value)
        prev_cursor = self._cursor

        def on_confirm(confirmed: bool) -> None:
            if not confirmed:
                return
            # Remove by index to avoid value-equality issues
            try:
                idx = self._project.objects.index(item)
                self._project.objects.pop(idx)
            except ValueError:
                return  # item already removed (shouldn't happen)
            self._save_toggle()  # persist in background
            # Re-render with cursor at previous position - 1 (D-11)
            target_cursor = max(0, prev_cursor - 1)
            self._set_project_with_cursor(self._project, target_cursor)
            self.app.notify(f"Deleted: {kind_val} '{value_display}'", markup=False)

        self.app.push_screen(
            ConfirmationModal(
                title="Delete Object",
                prompt=f"Delete {kind_val} '{value_display}'?",
            ),
            on_confirm,
        )

    def action_force_delete_object(self) -> None:
        """Delete highlighted object without confirmation (force delete D)."""
        item = self.highlighted_object
        if item is None:
            self.app.notify("No object selected", severity="error", markup=False)
            return
        prev_cursor = self._cursor
        try:
            idx = self._project.objects.index(item)
            self._project.objects.pop(idx)
        except ValueError:
            return
        self._save_toggle()
        target_cursor = max(0, prev_cursor - 1)
        self._set_project_with_cursor(self._project, target_cursor)
        kind_val = item.kind.value
        value_display = _truncate(item.label if item.label else item.value)
        self.app.notify(f"Deleted: {kind_val} '{value_display}'", markup=False)

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
