"""Top-right pane: MR status display with authored and review request sections.

Displays open MRs authored by the user and MRs requesting their review,
grouped into two sections. Each MR row shows number, title, pipeline status,
and review status. Navigation via j/k/up/down, Enter opens the MR URL.
"""
from __future__ import annotations

import subprocess

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from joy.models import MRDetail
from joy.widgets.icons import (
    ICON_ACTIONABLE,
    ICON_CI_FAIL,
    ICON_CI_PASS,
    ICON_CI_PENDING,
    ICON_MR_DRAFT,
    ICON_MR_OPEN,
    ICON_REVIEW_APPROVED,
    ICON_REVIEW_CHANGES,
    ICON_REVIEW_PENDING,
)


# ---------------------------------------------------------------------------
# _MRScroll: non-focusable scroll container (per _WorktreeScroll pattern)
# ---------------------------------------------------------------------------


class _MRScroll(VerticalScroll, can_focus=False):
    """Non-focusable scroll container for MR rows.

    Prevents VerticalScroll from stealing focus from MRPane.
    """


# ---------------------------------------------------------------------------
# GroupHeader: section header (duplicated from worktree_pane to avoid coupling)
# ---------------------------------------------------------------------------


class GroupHeader(Static):
    """Section header for My MRs / Review Requests."""

    DEFAULT_CSS = """
    GroupHeader {
        width: 1fr;
        height: 1;
        color: $text-muted;
        text-style: bold;
        padding: 0 1;
    }
    """


# ---------------------------------------------------------------------------
# MRRow: two-line row for a single MR entry
# ---------------------------------------------------------------------------


class MRRow(Static):
    """Two-line row: MR icon + number + title on line 1, repo + CI + review on line 2.

    Accepts an MRDetail and builds its own rich.Text content.
    """

    DEFAULT_CSS = """
    MRRow {
        width: 1fr;
        height: 2;
        padding: 0 1;
    }
    """

    def __init__(self, detail: MRDetail, *, max_width: int = 80, **kwargs) -> None:
        self.url: str = detail.url
        self.repo_name: str = detail.repo_name
        self.branch: str = detail.branch
        self.mr_number: int = detail.mr_number
        content = self.build_content(detail, max_width=max_width)
        super().__init__(content, **kwargs)

    @staticmethod
    def build_content(detail: MRDetail, max_width: int = 80) -> Text:
        """Build the rich.Text renderable for a two-line MR row.

        Line 1: MR icon + !number + title (pre-truncated to fit width)
        Line 2: repo name + CI status icon + review status (always visible)
        """
        t = Text(no_wrap=True, overflow="ellipsis")

        # Actionable dot: review requests are always actionable;
        # authored MRs are actionable when not draft AND (changes_requested
        # OR ci_failed OR (approved AND ci_pass)).
        if detail.is_review_request:
            actionable = True
        elif detail.is_draft:
            actionable = False
        else:
            actionable = (
                detail.review_status == "changes_requested"
                or detail.ci_status == "fail"
                or (detail.review_status == "approved" and detail.ci_status == "pass")
            )

        # Line 1: [dot] icon + number + title (pre-truncate title to fit)
        dot_prefix = f"{ICON_ACTIONABLE} " if actionable else "  "
        prefix = f"XX !{detail.mr_number}  "  # dot/space + icon + space + number
        title_budget = max(max_width - len(prefix), 5)
        title = detail.title
        if len(title) > title_budget:
            title = title[: title_budget - 1] + "\u2026"

        if actionable:
            t.append(f"{ICON_ACTIONABLE}", style="bold cyan")
        else:
            t.append(" ")

        if detail.is_draft:
            t.append(f"{ICON_MR_DRAFT}", style="dim")
        else:
            t.append(f"{ICON_MR_OPEN}", style="green")
        t.append(f" !{detail.mr_number}  ", style="bold")
        t.append(title)
        t.append("\n")

        # Line 2: repo + CI + review status (always visible, indented to align)
        t.append(f"   {detail.repo_name}", style="dim")

        if detail.ci_status == "pass":
            t.append(f"  {ICON_CI_PASS}", style="green")
        elif detail.ci_status == "fail":
            t.append(f"  {ICON_CI_FAIL}", style="red")
        elif detail.ci_status == "pending":
            t.append(f"  {ICON_CI_PENDING}", style="yellow")

        if detail.review_status == "approved":
            t.append(f"  {ICON_REVIEW_APPROVED} Approved", style="green")
        elif detail.review_status == "changes_requested":
            t.append(f"  {ICON_REVIEW_CHANGES} Changes", style="red")
        elif detail.review_status == "review_required":
            t.append(f"  {ICON_REVIEW_PENDING} Pending", style="dim")

        return t


# ---------------------------------------------------------------------------
# MRPane: main pane widget
# ---------------------------------------------------------------------------


class MRPane(Widget, can_focus=True):
    """Top-right pane: MR status display with authored and review request sections.

    Interactive -- j/k/arrows for cursor navigation, Enter/o to open MR URL.
    Data is pushed via set_mr_data().
    """

    BINDINGS = [
        Binding("escape", "focus_projects", "Back"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("j", "cursor_down", "Down"),
        Binding("enter", "activate_row", "Open"),
        Binding("o", "activate_row", "Open", show=False),
    ]

    DEFAULT_CSS = """
    MRPane {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    MRPane:focus-within {
        border: solid $accent;
    }
    MRPane:focus {
        border: solid $accent;
    }
    MRPane .empty-state {
        width: 1fr;
        height: 1fr;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
    }
    MRPane:focus-within MRRow.--highlight {
        background: $accent;
    }
    MRRow.--highlight {
        background: $accent 30%;
    }
    .section-spacer {
        height: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", "mr-pane")
        super().__init__(**kwargs)
        self.border_title = "MRs"
        self._cursor: int = -1
        self._rows: list[MRRow] = []

    def compose(self) -> ComposeResult:
        """Mount initial Loading... placeholder."""
        yield _MRScroll(
            Static("Loading\u2026", classes="empty-state"),
            id="mr-scroll",
        )

    async def set_mr_data(
        self,
        authored: list[MRDetail],
        review_requests: list[MRDetail],
    ) -> None:
        """Populate the pane with MR data in two sections.

        Args:
            authored: MRs authored by the current user.
            review_requests: MRs where the current user is a reviewer.
        """
        scroll = self.query_one("#mr-scroll", _MRScroll)

        # Save cursor identity for restore
        saved_identity: tuple[str, int] | None = None
        saved_index = self._cursor
        had_rows_before = len(self._rows) > 0
        if 0 <= self._cursor < len(self._rows):
            row = self._rows[self._cursor]
            saved_identity = (row.repo_name, row.mr_number)

        available_width = self._get_available_width()

        await scroll.remove_children()
        new_rows: list[MRRow] = []

        # Filter drafts from review requests (not actionable for reviewer)
        review_requests = [mr for mr in review_requests if not mr.is_draft]

        if not authored and not review_requests:
            self._rows = []
            self._cursor = -1
            await scroll.mount(
                Static("No open MRs", classes="empty-state")
            )
            return

        # Section 1: My MRs (sorted by mr_number desc)
        if authored:
            await scroll.mount(GroupHeader("My MRs"))
            for detail in sorted(authored, key=lambda d: d.mr_number, reverse=True):
                row = MRRow(detail, max_width=available_width)
                await scroll.mount(row)
                new_rows.append(row)

        # Spacer between sections
        if authored and review_requests:
            await scroll.mount(Static(" ", classes="section-spacer"))

        # Section 2: Review Requests (sorted by mr_number desc)
        if review_requests:
            await scroll.mount(GroupHeader("Review Requests"))
            for detail in sorted(review_requests, key=lambda d: d.mr_number, reverse=True):
                row = MRRow(detail, max_width=available_width)
                await scroll.mount(row)
                new_rows.append(row)

        self._rows = new_rows

        # Restore cursor by identity (repo_name, mr_number)
        if saved_identity is not None and new_rows:
            for i, row in enumerate(new_rows):
                if (row.repo_name, row.mr_number) == saved_identity:
                    self._cursor = i
                    break
            else:
                self._cursor = min(saved_index, len(new_rows) - 1)
        elif new_rows and not had_rows_before and saved_index == -1:
            self._cursor = 0
        elif new_rows and saved_index >= 0:
            self._cursor = min(saved_index, len(new_rows) - 1)
        else:
            self._cursor = -1

        self._update_highlight(emit=False)

    def set_refresh_label(
        self, timestamp: str, *, stale: bool = False, mr_error: bool = False
    ) -> None:
        """Update border_title with refresh timestamp."""
        parts = ["MRs"]
        if stale or mr_error:
            parts.append("\u26a0")
        if mr_error:
            parts.append("fetch failed")
        parts.append(timestamp)
        self.border_title = "  ".join(parts)

    def _get_available_width(self) -> int:
        """Return usable content width for title truncation."""
        width = self.content_region.width
        if width == 0:
            return 80  # safe default when widget not yet laid out
        return max(width - 2, 20)  # subtract 2 for padding, floor at 20

    def _update_highlight(self, *, emit: bool = True) -> None:
        """Update CSS highlight classes on rows."""
        for row in self._rows:
            row.remove_class("--highlight")
        if 0 <= self._cursor < len(self._rows):
            self._rows[self._cursor].add_class("--highlight")
            self._rows[self._cursor].scroll_visible()

    def clear_selection(self) -> None:
        """Clear selection: cursor=-1, remove all --highlight classes."""
        self._cursor = -1
        for r in self._rows:
            r.remove_class("--highlight")

    def action_cursor_up(self) -> None:
        if self._cursor > 0:
            self._cursor -= 1
            self._update_highlight()

    def action_cursor_down(self) -> None:
        if self._cursor < len(self._rows) - 1:
            self._cursor += 1
            self._update_highlight()

    def action_focus_projects(self) -> None:
        self.app.query_one("#project-list").focus()

    def action_activate_row(self) -> None:
        """Open the highlighted MR URL in the browser."""
        if self._cursor < 0 or self._cursor >= len(self._rows):
            return
        url = self._rows[self._cursor].url
        if url:
            subprocess.run(["open", url], check=False)
