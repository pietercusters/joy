"""ArchiveBrowserModal: two-section archive browser for unarchiving projects."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from joy.models import ArchivedProject, PresetKind


class _SectionHeader(Static):
    """Section divider label inside the archive browser."""

    DEFAULT_CSS = """
    _SectionHeader {
        width: 1fr;
        height: 1;
        color: $text-muted;
        text-style: bold;
        padding: 0 1;
        margin-top: 1;
    }
    """


class _ArchiveRow(Static):
    """Single row representing one archived project."""

    DEFAULT_CSS = """
    _ArchiveRow {
        width: 1fr;
        height: 1;
        padding: 0 1;
    }
    _ArchiveRow.--highlight {
        background: $accent;
    }
    """

    def __init__(self, ap: ArchivedProject, **kwargs) -> None:
        self.ap = ap
        label = self._build_label(ap)
        super().__init__(label, **kwargs)

    @staticmethod
    def _build_label(ap: ArchivedProject) -> str:
        archived_date = ap.archived_at.strftime("%Y-%m-%d")
        return f"  {ap.project.name}  ({archived_date})"


class ArchiveBrowserModal(ModalScreen["ArchivedProject | None"]):
    """Modal overlay listing archived projects in two sections.

    Top section: projects whose BRANCH object value matches a currently
    active worktree branch (branch-matched).
    Bottom section: all other archived projects.

    Both sections sorted by archived_at descending (latest first).

    Keys:
      up/down, j/k  — move cursor
      u             — unarchive selected project (restores to projects.toml)
      Escape        — close without action
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("u", "unarchive", "Unarchive"),
        Binding("escape", "cancel", "Close"),
    ]

    DEFAULT_CSS = """
    ArchiveBrowserModal {
        align: center middle;
    }
    ArchiveBrowserModal > Vertical {
        width: 70;
        max-height: 80%;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    ArchiveBrowserModal .modal-title {
        text-style: bold;
        width: 1fr;
        height: 1;
        margin-bottom: 1;
    }
    ArchiveBrowserModal .modal-hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        archived: list[ArchivedProject],
        active_branches: set[str],
    ) -> None:
        super().__init__()
        self._archived = archived
        self._active_branches = active_branches
        self._rows: list[_ArchiveRow] = []
        self._cursor: int = -1

    def _partition_by_branch(
        self,
    ) -> tuple[list[ArchivedProject], list[ArchivedProject]]:
        """Split archived projects into branch-matched and rest, sorted by archived_at desc."""
        matched: list[ArchivedProject] = []
        rest: list[ArchivedProject] = []
        for ap in self._archived:
            branch_objs = [o for o in ap.project.objects if o.kind == PresetKind.BRANCH]
            if any(o.value in self._active_branches for o in branch_objs):
                matched.append(ap)
            else:
                rest.append(ap)
        matched.sort(key=lambda ap: ap.archived_at, reverse=True)
        rest.sort(key=lambda ap: ap.archived_at, reverse=True)
        return matched, rest

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Archived Projects", classes="modal-title")
            yield VerticalScroll(id="archive-scroll")
            yield Static(
                "\u2191/\u2193 navigate  \u00b7  u: unarchive  \u00b7  Esc: close",
                classes="modal-hint",
            )

    def on_mount(self) -> None:
        self.focus()
        self._rebuild()

    def _rebuild(self) -> None:
        """Build section headers and rows inside the scroll container."""
        scroll = self.query_one("#archive-scroll", VerticalScroll)
        scroll.remove_children()
        self._rows = []

        matched, rest = self._partition_by_branch()

        if matched:
            scroll.mount(_SectionHeader("Active Branch"))
            for ap in matched:
                row = _ArchiveRow(ap)
                scroll.mount(row)
                self._rows.append(row)

        if rest:
            scroll.mount(_SectionHeader("Other"))
            for ap in rest:
                row = _ArchiveRow(ap)
                scroll.mount(row)
                self._rows.append(row)

        self._cursor = 0 if self._rows else -1
        self._update_highlight()

    def _update_highlight(self) -> None:
        """Apply/remove --highlight class based on current cursor position."""
        for row in self._rows:
            row.remove_class("--highlight")
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].add_class("--highlight")
            self._rows[self._cursor].scroll_visible()

    def action_cursor_up(self) -> None:
        if self._cursor > 0:
            self._cursor -= 1
            self._update_highlight()

    def action_cursor_down(self) -> None:
        if self._cursor < len(self._rows) - 1:
            self._cursor += 1
            self._update_highlight()

    def action_unarchive(self) -> None:
        """Return the selected ArchivedProject to the caller for restoration."""
        if 0 <= self._cursor < len(self._rows):
            selected_ap = self._rows[self._cursor].ap
            self.dismiss(selected_ap)

    def action_cancel(self) -> None:
        """Close modal without unarchiving anything."""
        self.dismiss(None)
